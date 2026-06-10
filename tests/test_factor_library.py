"""Tests for factor_library — TDD: write tests first, implement to make them pass.

Pure function tests (compute_ic, classify_factor, _compute_factor) run without DB.
DB-dependent tests (get_factor_context) require the FactorScore model from Step 3.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from agents.factor_library import ALPHA_BUCKETS, _compute_factor, classify_factor, compute_ic

# ── compute_ic ─────────────────────────────────────────────────────────────────

def test_compute_ic_perfect_positive():
    s = pd.Series(range(50), dtype=float)
    assert compute_ic(s, s) == pytest.approx(1.0)


def test_compute_ic_perfect_negative():
    s = pd.Series(range(50), dtype=float)
    neg = s * -1
    assert compute_ic(s, neg) == pytest.approx(-1.0)


def test_compute_ic_unrelated_series():
    rng = np.random.default_rng(42)
    a = pd.Series(rng.random(100))
    b = pd.Series(rng.random(100))
    ic = compute_ic(a, b)
    assert abs(ic) < 0.3  # random series should have low IC


def test_compute_ic_returns_zero_when_too_few_obs():
    short = pd.Series([1.0, 2.0, 3.0])  # < _MIN_OBS (30)
    assert compute_ic(short, short) == 0.0


def test_compute_ic_handles_nan_rows():
    a = pd.Series([float("nan"), 1.0, 2.0, 3.0] * 15)
    b = pd.Series([1.0, 2.0, 3.0, 4.0] * 15)
    ic = compute_ic(a, b)
    assert isinstance(ic, float)


# ── classify_factor ────────────────────────────────────────────────────────────

def test_classify_alive():
    assert classify_factor(0.10) == "alive"
    assert classify_factor(0.50) == "alive"


def test_classify_reversed():
    assert classify_factor(-0.10) == "reversed"
    assert classify_factor(-0.50) == "reversed"


def test_classify_dead_near_zero():
    assert classify_factor(0.04) == "dead"
    assert classify_factor(-0.04) == "dead"
    assert classify_factor(0.0) == "dead"


def test_classify_boundary_exactly_at_threshold():
    # 0.05 is the boundary — should be alive (|ic| not < 0.05)
    assert classify_factor(0.05) == "alive"
    assert classify_factor(-0.05) == "reversed"


# ── _compute_factor ────────────────────────────────────────────────────────────

def _make_prices(n: int = 300, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = pd.Series(100 + rng.random(n).cumsum())
    volume = pd.Series(rng.integers(1_000_000, 5_000_000, n).astype(float))
    return pd.DataFrame({"Close": close, "Volume": volume})


def test_compute_factor_ret_1m_has_no_value_in_first_20_rows():
    prices = _make_prices()
    result = _compute_factor("ret_1m", prices)
    assert result.iloc[:20].isna().all()


def test_compute_factor_ret_3m_length_matches_prices():
    prices = _make_prices()
    result = _compute_factor("ret_3m", prices)
    assert len(result) == len(prices)


def test_compute_factor_realized_vol_is_non_negative():
    prices = _make_prices()
    result = _compute_factor("realized_vol_20d", prices).dropna()
    assert (result >= 0).all()


def test_compute_factor_turnover_ratio_is_positive():
    prices = _make_prices()
    result = _compute_factor("turnover_ratio", prices).dropna()
    assert (result > 0).all()


def test_compute_factor_ret_consistency_bounds():
    prices = _make_prices()
    result = _compute_factor("ret_consistency_3m", prices).dropna()
    assert result.between(0, 1).all()


def test_compute_factor_unknown_name_returns_empty():
    prices = _make_prices()
    result = _compute_factor("nonexistent_factor", prices)
    assert result.empty


def test_all_bucket_factors_produce_output():
    prices = _make_prices(n=300)
    for _bucket, factors in ALPHA_BUCKETS.items():
        for name in factors:
            result = _compute_factor(name, prices)
            assert isinstance(result, pd.Series), f"{name} did not return a Series"


# ── score_ticker_factors ───────────────────────────────────────────────────────

async def test_score_ticker_factors_returns_all_factors():
    prices = _make_prices(n=300)
    prices.index = pd.date_range("2023-01-01", periods=300, freq="B")

    with patch("agents.factor_library._fetch_prices", return_value=prices):
        from agents.factor_library import score_ticker_factors
        results = await score_ticker_factors("AAPL")

    expected_count = sum(len(v) for v in ALPHA_BUCKETS.values())
    assert len(results) == expected_count


async def test_score_ticker_factors_returns_empty_on_insufficient_data():
    tiny = _make_prices(n=50)
    with patch("agents.factor_library._fetch_prices", return_value=tiny):
        from agents.factor_library import score_ticker_factors
        results = await score_ticker_factors("AAPL")
    assert results == []


async def test_score_ticker_factors_returns_empty_on_empty_dataframe():
    with patch("agents.factor_library._fetch_prices", return_value=pd.DataFrame()):
        from agents.factor_library import score_ticker_factors
        results = await score_ticker_factors("AAPL")
    assert results == []


async def test_score_ticker_factors_result_schema():
    prices = _make_prices(n=300)
    prices.index = pd.date_range("2023-01-01", periods=300, freq="B")
    with patch("agents.factor_library._fetch_prices", return_value=prices):
        from agents.factor_library import score_ticker_factors
        results = await score_ticker_factors("AAPL")

    for r in results:
        assert "name" in r
        assert "bucket" in r
        assert "ic" in r
        assert "status" in r
        assert r["status"] in {"alive", "reversed", "dead"}
        assert -1.0 <= r["ic"] <= 1.0


# ── get_factor_context (requires FactorScore model — Step 3) ──────────────────

async def test_get_factor_context_returns_empty_when_no_scores(db_session, db_engine):
    from agents.factor_library import get_factor_context
    result = await get_factor_context("AAPL")
    assert result == ""


async def test_get_factor_context_formats_alive_factors(db_session, db_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from memory.database import FactorScore

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(FactorScore(ticker="AAPL", name="ret_3m", bucket="momentum", ic=0.38, status="alive"))
        s.add(FactorScore(
            ticker="AAPL", name="realized_vol_20d", bucket="volatility", ic=-0.25, status="reversed"
        ))
        s.add(FactorScore(ticker="AAPL", name="ret_1m", bucket="momentum", ic=0.02, status="dead"))
        await s.commit()

    from agents.factor_library import get_factor_context
    result = await get_factor_context("AAPL")

    assert "ret_3m" in result
    assert "realized_vol_20d" in result  # reversed is included
    assert "ret_1m" not in result         # dead is excluded
    assert "IC=" in result


async def test_get_factor_context_excludes_other_tickers(db_session, db_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from memory.database import FactorScore

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(FactorScore(ticker="TSLA", name="ret_3m", bucket="momentum", ic=0.40, status="alive"))
        await s.commit()

    from agents.factor_library import get_factor_context
    result = await get_factor_context("AAPL")
    assert result == ""
