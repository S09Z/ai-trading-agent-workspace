"""Tests for the walk-forward backtest engine — yfinance mocked, no network."""

from unittest.mock import patch

import numpy as np
import pandas as pd

from backtesting.engine import print_report, run_backtest


def _make_prices(n: int) -> pd.DataFrame:
    idx = pd.bdate_range("2022-01-03", periods=n)
    rng = np.random.default_rng(42)
    close = pd.Series(100 * np.cumprod(1 + rng.normal(0.0005, 0.01, n)), index=idx)
    volume = pd.Series(rng.integers(1_000_000, 5_000_000, n).astype(float), index=idx)
    return pd.DataFrame({"Close": close, "Volume": volume})


def test_no_trades_when_score_below_threshold():
    prices = _make_prices(380)
    with patch("backtesting.engine._fetch_prices", return_value=prices), \
         patch("backtesting.engine._composite_from_ics", return_value=10.0):
        result = run_backtest("TEST", train_days=252, test_days=63, hold_days=5, entry_score=50.0)

    assert result["n_trades"] == 0


def test_trades_generated_when_score_above_threshold():
    prices = _make_prices(380)
    with patch("backtesting.engine._fetch_prices", return_value=prices), \
         patch("backtesting.engine._composite_from_ics", return_value=80.0):
        result = run_backtest("TEST", train_days=252, test_days=63, hold_days=5, entry_score=50.0)

    assert result["n_trades"] == result["n_windows"] > 0


def test_no_lookahead_bias():
    """Training slices must be exactly train_days long and end before the test entry."""
    prices = _make_prices(380)
    train_days, test_days = 252, 63
    seen_slices: list[pd.DataFrame] = []

    def record_slice(df):
        seen_slices.append(df)
        return {}

    with patch("backtesting.engine._fetch_prices", return_value=prices), \
         patch("backtesting.engine._train_ics", side_effect=record_slice):
        run_backtest("TEST", train_days=train_days, test_days=test_days,
                     hold_days=5, entry_score=50.0)

    assert seen_slices
    for i, sl in enumerate(seen_slices):
        assert len(sl) == train_days
        entry_date = prices.index[i * test_days + train_days]
        assert sl.index[-1] < entry_date


def test_window_count_correct():
    # 380 rows, 252 train / 63 test → starts at 0 and 63 → 2 windows
    prices = _make_prices(380)
    with patch("backtesting.engine._fetch_prices", return_value=prices), \
         patch("backtesting.engine._composite_from_ics", return_value=0.0):
        result = run_backtest("TEST", train_days=252, test_days=63, hold_days=5, entry_score=50.0)

    assert result["n_windows"] == 2


def test_report_prints_all_tickers(capsys):
    results = [
        {"ticker": "NVDA", "n_trades": 3, "n_windows": 4, "sharpe": 1.2,
         "cagr": 0.30, "max_drawdown": -0.10, "win_rate": 0.66, "trades": [0.1, 0.05, -0.02]},
        {"ticker": "AAPL", "n_trades": 0, "n_windows": 4, "sharpe": 0.0,
         "cagr": 0.0, "max_drawdown": 0.0, "win_rate": 0.0, "trades": []},
    ]
    print_report(results, hold_days=5, entry_score=50.0, train_days=252, test_days=63)

    out = capsys.readouterr().out
    assert "NVDA" in out
    assert "AAPL" in out
    assert "PORTFOLIO" in out
