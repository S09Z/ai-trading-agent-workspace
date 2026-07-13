"""Smart Money Concepts (SMC) detectors — pure functions over OHLCV candles.

Each detector takes a pandas DataFrame with columns Open/High/Low/Close/Volume
and a DatetimeIndex, and returns a list of SMCDetection records. Detectors are
interval-agnostic — they operate on whatever candles they are handed.
"""
from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass(frozen=True)
class SMCDetection:
    pattern: str        # "fvg" | "order_block" | "liquidity_sweep"
    bias: str           # "bullish" | "bearish"
    bar_index: int      # positional index of the bar the pattern fires on
    timestamp: datetime
    zone_low: float
    zone_high: float
    strength: float     # normalized magnitude (see per-detector docstring)


def detect_fvg(df: pd.DataFrame) -> list[SMCDetection]:
    """3-candle Fair Value Gap. Fires on candle i; strength = gap size / close[i]."""
    high, low, close = df["High"].to_numpy(), df["Low"].to_numpy(), df["Close"].to_numpy()
    out: list[SMCDetection] = []
    for i in range(2, len(df)):
        ts = df.index[i].to_pydatetime()
        if low[i] > high[i - 2]:  # bullish gap
            gap = low[i] - high[i - 2]
            strength = float(gap / close[i]) if close[i] != 0.0 else float("nan")
            out.append(SMCDetection("fvg", "bullish", i, ts,
                                    float(high[i - 2]), float(low[i]), strength))
        elif high[i] < low[i - 2]:  # bearish gap
            gap = low[i - 2] - high[i]
            strength = float(gap / close[i]) if close[i] != 0.0 else float("nan")
            out.append(SMCDetection("fvg", "bearish", i, ts,
                                    float(high[i]), float(low[i - 2]), strength))
    return out


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range over `period` bars."""
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(period).mean()


def detect_order_block(df: pd.DataFrame, impulse_atr_mult: float) -> list[SMCDetection]:
    """Last opposing candle before an impulsive displacement (> mult × ATR14).

    Fires on the order-block candle (bar before the impulse). strength = body / ATR14.
    """
    o, c = df["Open"].to_numpy(), df["Close"].to_numpy()
    high, low = df["High"].to_numpy(), df["Low"].to_numpy()
    atr = _atr(df).to_numpy()
    out: list[SMCDetection] = []
    for i in range(1, len(df)):
        if pd.isna(atr[i]) or atr[i] <= 0:
            continue
        body = c[i] - o[i]
        threshold = impulse_atr_mult * atr[i]
        ob = i - 1
        ts = df.index[ob].to_pydatetime()
        if body > threshold and c[ob] < o[ob]:        # impulse up after a down candle
            out.append(SMCDetection("order_block", "bullish", ob, ts,
                                    float(low[ob]), float(high[ob]), float(body / atr[i])))
        elif body < -threshold and c[ob] > o[ob]:      # impulse down after an up candle
            out.append(SMCDetection("order_block", "bearish", ob, ts,
                                    float(low[ob]), float(high[ob]), float(-body / atr[i])))
    return out


def detect_liquidity_sweep(df: pd.DataFrame, swing_lookback: int) -> list[SMCDetection]:
    """Wick beyond the prior `swing_lookback`-bar high/low that closes back inside.

    strength = wick overshoot / ATR14.
    """
    high, low, close = df["High"].to_numpy(), df["Low"].to_numpy(), df["Close"].to_numpy()
    atr = _atr(df).to_numpy()
    out: list[SMCDetection] = []
    for i in range(swing_lookback, len(df)):
        prior_high = float(high[i - swing_lookback:i].max())
        prior_low = float(low[i - swing_lookback:i].min())
        denom = atr[i] if not pd.isna(atr[i]) and atr[i] > 0 else 1.0
        ts = df.index[i].to_pydatetime()
        if high[i] > prior_high and close[i] < prior_high:      # buy-side liquidity swept
            out.append(SMCDetection("liquidity_sweep", "bearish", i, ts,
                                    prior_high, prior_high, float((high[i] - prior_high) / denom)))
        if low[i] < prior_low and close[i] > prior_low:         # sell-side liquidity swept
            out.append(SMCDetection("liquidity_sweep", "bullish", i, ts,
                                    prior_low, prior_low, float((prior_low - low[i]) / denom)))
    return out


def detect_all(
    df: pd.DataFrame, *, impulse_atr_mult: float, swing_lookback: int
) -> list[SMCDetection]:
    """Run all three detectors and return the combined detections."""
    return (
        detect_fvg(df)
        + detect_order_block(df, impulse_atr_mult)
        + detect_liquidity_sweep(df, swing_lookback)
    )


_PATTERN_LABELS: dict[str, str] = {
    "fvg": "FVG",
    "order_block": "Order Block",
    "liquidity_sweep": "Liquidity Sweep",
}


async def get_smc_context(ticker: str) -> str:
    """Format recent SMC detections with historical edge stats as a prompt section.

    Returns empty string if no candles or no detections (graceful fallback for analysts).
    """
    from sqlalchemy import select

    from collectors.market_data import fetch_ohlcv
    from config.settings import get_settings
    from memory.database import AsyncSessionLocal, SMCEdgeStat

    s = get_settings()
    candles = await fetch_ohlcv(ticker, period=s.smc_period, interval=s.smc_interval)
    if not candles:
        return ""

    df = pd.DataFrame([
        {"Open": c["open"], "High": c["high"], "Low": c["low"],
         "Close": c["close"], "Volume": c["volume"]}
        for c in candles
    ])
    df.index = pd.DatetimeIndex([c["timestamp"] for c in candles])

    detections = detect_all(
        df, impulse_atr_mult=s.smc_impulse_atr_mult, swing_lookback=s.smc_swing_lookback
    )
    if not detections:
        return ""

    async with AsyncSessionLocal() as session:
        edge_rows = (await session.execute(select(SMCEdgeStat))).scalars().all()
    edge = {(r.pattern, r.bias): r for r in edge_rows}

    lines = []
    for d in detections[-10:]:
        stat = edge.get((d.pattern, d.bias))
        label = _PATTERN_LABELS.get(d.pattern, d.pattern)
        date_str = d.timestamp.strftime("%Y-%m-%d")
        if stat:
            lines.append(
                f"  SMC: {d.bias.capitalize()} {label} @ {date_str}"
                f" (hist: {stat.mean_fwd_return:+.1%} {s.smc_horizon_days}d,"
                f" {stat.hit_rate:.0%} hit, n={stat.sample_size})"
            )
        else:
            lines.append(f"  SMC: {d.bias.capitalize()} {label} @ {date_str}")

    return "SMC Detections:\n" + "\n".join(lines)
