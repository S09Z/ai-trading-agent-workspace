"""Performance metrics for the walk-forward backtest — pure functions on trade returns."""

import numpy as np

_TRADING_DAYS = 252


def sharpe_ratio(returns: list[float], hold_days: int = 5) -> float:
    """Annualised Sharpe of per-trade returns; 0.0 when undefined (empty / zero std)."""
    if len(returns) < 2:
        return 0.0
    r = np.asarray(returns)
    std = r.std(ddof=1)
    if std == 0:
        return 0.0
    return float(r.mean() / std * np.sqrt(_TRADING_DAYS / hold_days))


def cagr(returns: list[float], hold_days: int = 5) -> float:
    """Annualised compound growth rate assuming each trade spans `hold_days` trading days."""
    if not returns:
        return 0.0
    final = float(np.prod([1 + r for r in returns]))
    if final <= 0:
        return -1.0
    years = len(returns) * hold_days / _TRADING_DAYS
    return float(final ** (1 / years) - 1)


def max_drawdown(returns: list[float]) -> float:
    """Largest peak-to-trough decline on the compounded equity curve (negative or 0.0)."""
    if not returns:
        return 0.0
    equity = np.cumprod([1.0] + [1 + r for r in returns])
    peaks = np.maximum.accumulate(equity)
    return float((equity / peaks - 1).min())


def win_rate(returns: list[float]) -> float:
    """Fraction of trades with positive return; 0.0 on empty."""
    if not returns:
        return 0.0
    return sum(1 for r in returns if r > 0) / len(returns)
