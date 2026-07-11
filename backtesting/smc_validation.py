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
