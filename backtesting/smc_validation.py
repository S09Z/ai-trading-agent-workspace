"""SMC event-study validation.

For each detection at bar t, measure the `horizon`-bar forward return, sign-adjust
by pattern bias (bullish → +1, bearish → −1), and aggregate per (pattern, bias,
interval) into mean forward return + directional hit-rate. Trusted only when the
event count clears `smc_min_events`. Persisted as SMCEdgeStat.
"""
import pandas as pd


def forward_return(close: pd.Series, bar_index: int, horizon: int) -> float | None:
    """close[t+horizon] / close[t] − 1, or None if t+horizon is out of range."""
    if bar_index + horizon >= len(close):
        return None
    c0 = float(close.iloc[bar_index])
    c1 = float(close.iloc[bar_index + horizon])
    if c0 <= 0:
        return None
    return c1 / c0 - 1


def aggregate(edges: list[float], min_events: int) -> dict | None:
    """Aggregate bias-sign-adjusted edges. None if fewer than `min_events`."""
    if len(edges) < min_events:
        return None
    return {
        "sample_size": len(edges),
        "mean_fwd_return": round(sum(edges) / len(edges), 6),
        "hit_rate": round(sum(1 for e in edges if e > 0) / len(edges), 6),
    }


import asyncio

from agents.smc import detect_all
from config.settings import get_settings


def event_study(
    prices_by_ticker: dict[str, pd.DataFrame],
    *,
    interval: str,
    horizon: int,
    min_events: int,
    impulse_atr_mult: float,
    swing_lookback: int,
) -> list[dict]:
    """Run detectors across all tickers, aggregate edges per (pattern, bias)."""
    edges: dict[tuple[str, str], list[float]] = {}
    for df in prices_by_ticker.values():
        if len(df) < horizon + 3:
            continue
        close = df["Close"]
        for d in detect_all(df, impulse_atr_mult=impulse_atr_mult, swing_lookback=swing_lookback):
            fr = forward_return(close, d.bar_index, horizon)
            if fr is None:
                continue
            edge = fr if d.bias == "bullish" else -fr
            edges.setdefault((d.pattern, d.bias), []).append(edge)

    out: list[dict] = []
    for (pattern, bias), vals in edges.items():
        stat = aggregate(vals, min_events)
        if stat is None:
            continue
        out.append({"pattern": pattern, "bias": bias, "interval": interval, **stat})
    return out


def _fetch_prices(ticker: str, interval: str) -> pd.DataFrame:
    import yfinance as yf
    period = "2y" if interval == "1d" else "60d"
    return yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)


async def run_smc_validation() -> list[dict]:
    """Fetch watchlist history, run the event study, and upsert SMCEdgeStat rows."""
    from sqlalchemy import delete

    from memory.database import AsyncSessionLocal, SMCEdgeStat

    s = get_settings()
    prices = {}
    for t in s.watchlist:
        df = await asyncio.to_thread(_fetch_prices, t, s.smc_interval)
        if not df.empty:
            prices[t] = df

    stats = event_study(
        prices, interval=s.smc_interval, horizon=s.smc_horizon_days,
        min_events=s.smc_min_events, impulse_atr_mult=s.smc_impulse_atr_mult,
        swing_lookback=s.smc_swing_lookback,
    )

    async with AsyncSessionLocal() as session:
        await session.execute(delete(SMCEdgeStat).where(SMCEdgeStat.interval == s.smc_interval))
        session.add_all([SMCEdgeStat(**row) for row in stats])
        await session.commit()
    return stats


def main() -> None:
    stats = asyncio.run(run_smc_validation())
    print("╔══ SMC Event-Study Validation ══╗")
    if not stats:
        print("  No pattern cleared the min-events threshold.")
        return
    for r in sorted(stats, key=lambda x: x["mean_fwd_return"], reverse=True):
        print(f"  {r['pattern']:<16} {r['bias']:<8} "
              f"n={r['sample_size']:<5} mean={r['mean_fwd_return']:+.4f} hit={r['hit_rate']:.2%}")


if __name__ == "__main__":
    main()
