"""Walk-forward backtest of the composite-score strategy.

For each rolling window: compute factor ICs on the training slice only
(no lookahead), derive the composite score exactly as the live scorer does
(mean(signed IC) per bucket × 1000, clamped to [0, 100]), and enter a long trade at the
first test-window close when the score clears the entry threshold.

Run: uv run python -m backtesting.engine [--tickers AAPL NVDA] [--hold-days N]
"""
import argparse

import pandas as pd

from agents.factor_library import ALPHA_BUCKETS, _compute_factor, compute_ic
from backtesting.metrics import cagr, max_drawdown, sharpe_ratio, win_rate

_IC_SCALE = 1000.0  # matches intelligence/composite_scorer.py


def _train_ics(prices: pd.DataFrame) -> dict[str, float]:
    """Compute per-factor Spearman ICs on a training-window price slice."""
    forward_return = prices["Close"].squeeze().pct_change(5).shift(-5)
    ics: dict[str, float] = {}
    for factors in ALPHA_BUCKETS.values():
        for name in factors:
            ics[name] = compute_ic(_compute_factor(name, prices), forward_return)
    return ics


def _composite_from_ics(ics: dict[str, float]) -> float:
    """Replicate compute_composite() scoring without DB reads (uses signed IC)."""
    bucket_scores = []
    for factors in ALPHA_BUCKETS.values():
        vals = [ics[f] for f in factors if f in ics]
        if vals:
            bucket_scores.append(sum(vals) / len(vals) * _IC_SCALE)
    if not bucket_scores:
        return 0.0
    composite = sum(bucket_scores) / len(bucket_scores)
    return max(0.0, min(100.0, composite))


def _fetch_prices(ticker: str) -> pd.DataFrame:
    import yfinance as yf
    return yf.download(ticker, period="3y", interval="1d", progress=False, auto_adjust=True)


def run_backtest(
    ticker: str,
    *,
    train_days: int = 252,
    test_days: int = 63,
    hold_days: int = 5,
    entry_score: float = 50.0,
) -> dict:
    """Walk-forward backtest one ticker. Returns metrics dict (trades may be empty)."""
    prices = _fetch_prices(ticker)
    trades: list[float] = []
    n_windows = 0

    if not prices.empty and len(prices) >= train_days + test_days:
        close = prices["Close"].squeeze()
        for start in range(0, len(prices) - train_days - test_days + 1, test_days):
            n_windows += 1
            train_slice = prices.iloc[start : start + train_days]
            score = _composite_from_ics(_train_ics(train_slice))

            entry_idx = start + train_days
            exit_idx = entry_idx + hold_days
            if score >= entry_score and exit_idx < len(prices):
                entry = float(close.iloc[entry_idx])
                exit_ = float(close.iloc[exit_idx])
                trades.append((exit_ - entry) / entry)

    return {
        "ticker": ticker,
        "n_trades": len(trades),
        "n_windows": n_windows,
        "sharpe": sharpe_ratio(trades, hold_days),
        "cagr": cagr(trades, hold_days),
        "max_drawdown": max_drawdown(trades),
        "win_rate": win_rate(trades),
        "trades": trades,
    }


def run_all(tickers: list[str], **params) -> list[dict]:
    return [run_backtest(t, **params) for t in tickers]


def print_report(
    results: list[dict],
    *,
    hold_days: int,
    entry_score: float,
    train_days: int,
    test_days: int,
) -> None:
    print("╔══ AlphaOps Walk-Forward Backtest ══╗")
    print(f"  Strategy: composite score ≥ {entry_score:.0f}, hold {hold_days}d")
    print(f"  Windows: {train_days}d train / {test_days}d test\n")
    header = f"{'TICKER':<10}{'TRADES':>7}{'SHARPE':>8}{'CAGR':>9}{'MAX-DD':>9}{'WIN%':>6}"
    print(header)

    def row(label: str, r: dict) -> str:
        return (
            f"{label:<10}{r['n_trades']:>7}{r['sharpe']:>8.2f}"
            f"{r['cagr']:>8.1%}{r['max_drawdown']:>9.1%}{r['win_rate']:>6.0%}"
        )

    for r in results:
        print(row(r["ticker"], r))

    all_trades = [t for r in results for t in r["trades"]]
    portfolio = {
        "n_trades": len(all_trades),
        "sharpe": sharpe_ratio(all_trades, hold_days),
        "cagr": cagr(all_trades, hold_days),
        "max_drawdown": max_drawdown(all_trades),
        "win_rate": win_rate(all_trades),
    }
    print("─" * len(header))
    print(row("PORTFOLIO", portfolio))


def main() -> None:
    from config.settings import get_settings

    settings = get_settings()
    parser = argparse.ArgumentParser(description="Walk-forward backtest on watchlist tickers")
    parser.add_argument("--tickers", nargs="+", default=settings.watchlist)
    parser.add_argument("--hold-days", type=int, default=settings.backtest_hold_days)
    parser.add_argument("--entry-score", type=float, default=settings.backtest_entry_score)
    args = parser.parse_args()

    params = {
        "train_days": settings.backtest_train_days,
        "test_days": settings.backtest_test_days,
        "hold_days": args.hold_days,
        "entry_score": args.entry_score,
    }
    results = run_all(args.tickers, **params)
    print_report(results, **params)


if __name__ == "__main__":
    main()
