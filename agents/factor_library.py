"""Alpha factor library — computes IC/IR-scored factors per ticker.

Factors are time-series: for each date t, the factor value is correlated
against the 5-day forward return starting at t+1 (Information Coefficient).
IC > 0.05  → alive (positively predictive)
IC < -0.05 → reversed (negatively predictive — still useful, flip sign)
|IC| ≤ 0.05 → dead (no predictive power)
"""
import asyncio

import pandas as pd
from scipy.stats import spearmanr

ALPHA_BUCKETS: dict[str, list[str]] = {
    "momentum":   ["ret_1m", "ret_3m", "ret_6m", "ret_12m"],
    "volatility": ["realized_vol_20d", "realized_vol_60d"],
    "liquidity":  ["turnover_ratio"],
    "quality":    ["ret_consistency_3m"],
}

# Minimum observations needed to compute a meaningful IC
_MIN_OBS = 30


def compute_ic(factor: pd.Series, forward_return: pd.Series) -> float:
    """Spearman rank IC between factor values and 5-day forward returns."""
    combined = pd.concat([factor, forward_return], axis=1).dropna()
    if len(combined) < _MIN_OBS:
        return 0.0
    col_a, col_b = combined.iloc[:, 0], combined.iloc[:, 1]
    # Spearman is undefined for constant series — return 0 (no predictive signal)
    if col_a.nunique() < 2 or col_b.nunique() < 2:
        return 0.0
    corr, _ = spearmanr(col_a, col_b)
    return float(corr) if not pd.isna(corr) else 0.0


def classify_factor(ic: float) -> str:
    if abs(ic) < 0.05:
        return "dead"
    return "alive" if ic > 0 else "reversed"


def _compute_factor(factor_name: str, prices: pd.DataFrame) -> pd.Series:
    """Return a time-series of factor values given OHLCV prices."""
    close = prices["Close"].squeeze()
    volume = prices["Volume"].squeeze()
    daily_ret = close.pct_change()
    avg_vol = volume.rolling(20).mean()

    dispatch: dict[str, pd.Series] = {
        "ret_1m":             close.pct_change(21),
        "ret_3m":             close.pct_change(63),
        "ret_6m":             close.pct_change(126),
        "ret_12m":            close.pct_change(252),
        "realized_vol_20d":   daily_ret.rolling(20).std(),
        "realized_vol_60d":   daily_ret.rolling(60).std(),
        "turnover_ratio":     volume / avg_vol.where(avg_vol > 0),
        "ret_consistency_3m": daily_ret.rolling(63).apply(
            lambda x: (x > 0).mean(), raw=True
        ),
    }
    return dispatch.get(factor_name, pd.Series(dtype=float))


def _fetch_prices(ticker: str) -> pd.DataFrame:
    """Synchronous yfinance download — call via asyncio.to_thread."""
    import yfinance as yf
    df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=True)
    return df


async def score_ticker_factors(ticker: str) -> list[dict]:
    """Download 2y of prices and compute IC/IR for every factor in ALPHA_BUCKETS.

    Returns a list of dicts ready to be inserted as FactorScore rows.
    Empty list if data is insufficient.
    """
    prices = await asyncio.to_thread(_fetch_prices, ticker)
    if prices.empty or len(prices) < 100:
        return []

    forward_return = prices["Close"].squeeze().pct_change(5).shift(-5)

    results: list[dict] = []
    for bucket, factors in ALPHA_BUCKETS.items():
        for factor_name in factors:
            factor_vals = _compute_factor(factor_name, prices)
            ic = compute_ic(factor_vals, forward_return)
            results.append({
                "name": factor_name,
                "bucket": bucket,
                "ic": round(ic, 4),
                "status": classify_factor(ic),
            })
    return results


async def get_factor_context(ticker: str) -> str:
    """Query FactorScore table for alive factors and format as a prompt section.

    Returns empty string if no scores exist yet (first run — fallback to static metrics).
    """
    from sqlalchemy import select

    from memory.database import AsyncSessionLocal, FactorScore

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(FactorScore)
            .where(FactorScore.ticker == ticker, FactorScore.status.in_(["alive", "reversed"]))
            .order_by(FactorScore.ic.desc())
            .limit(10)
        )).scalars().all()

    if not rows:
        return ""

    lines = [
        f"  {r.name} [{r.bucket}] IC={r.ic:+.3f} ({r.status})"
        for r in rows
    ]
    return "Alpha Factors (IC vs 5d forward return):\n" + "\n".join(lines)
