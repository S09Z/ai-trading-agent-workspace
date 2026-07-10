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
            out.append(SMCDetection("fvg", "bullish", i, ts,
                                    float(high[i - 2]), float(low[i]), float(gap / close[i])))
        elif high[i] < low[i - 2]:  # bearish gap
            gap = low[i - 2] - high[i]
            out.append(SMCDetection("fvg", "bearish", i, ts,
                                    float(high[i]), float(low[i - 2]), float(gap / close[i])))
    return out
