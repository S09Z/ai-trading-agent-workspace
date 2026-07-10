"""Tests for backtest performance metrics — pure unit, no DB, no yfinance."""

import pytest

from backtesting.metrics import cagr, max_drawdown, sharpe_ratio, win_rate

# ── sharpe_ratio ───────────────────────────────────────────────────────────────

def test_sharpe_zero_on_empty_returns():
    assert sharpe_ratio([]) == 0.0


def test_sharpe_zero_on_zero_std():
    assert sharpe_ratio([0.01, 0.01, 0.01]) == 0.0


def test_sharpe_positive_on_consistent_wins():
    assert sharpe_ratio([0.01, 0.02, 0.03]) > 0.0


# ── cagr ───────────────────────────────────────────────────────────────────────

def test_cagr_correct_single_trade():
    # one 10% trade held 5 days, annualised over 252/5 periods
    expected = 1.10 ** (252 / 5) - 1
    assert cagr([0.10], hold_days=5) == pytest.approx(expected)


def test_cagr_compounds_correctly():
    # 1.10 * 0.95 over 2 trades × 5 days
    expected = (1.10 * 0.95) ** (252 / 10) - 1
    assert cagr([0.10, -0.05], hold_days=5) == pytest.approx(expected)


# ── max_drawdown ───────────────────────────────────────────────────────────────

def test_max_drawdown_negative_on_loss():
    assert max_drawdown([-0.10]) == pytest.approx(-0.10)


def test_max_drawdown_zero_on_monotone_gains():
    assert max_drawdown([0.01, 0.02, 0.03]) == 0.0


# ── win_rate ───────────────────────────────────────────────────────────────────

def test_win_rate_correct():
    assert win_rate([0.05, -0.02, 0.01, -0.01]) == pytest.approx(0.5)


def test_win_rate_zero_on_empty():
    assert win_rate([]) == 0.0


def test_win_rate_one_on_all_positive():
    assert win_rate([0.01, 0.02]) == pytest.approx(1.0)
