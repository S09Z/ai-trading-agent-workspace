"""Tests for CompositeScorer — TDD: tests written before/with implementation.

Pure-function tests (_grade) run without DB.
DB-dependent tests (compute_composite) use the real test DB via db_session fixture.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from memory.database import FactorScore

# ── _grade (pure function) ─────────────────────────────────────────────────────

def test_grade_s_at_boundary():
    from intelligence.composite_scorer import _grade
    assert _grade(75.0) == "S"


def test_grade_a_just_below_s():
    from intelligence.composite_scorer import _grade
    assert _grade(74.9) == "A"


def test_grade_a_at_boundary():
    from intelligence.composite_scorer import _grade
    assert _grade(60.0) == "A"


def test_grade_b_just_below_a():
    from intelligence.composite_scorer import _grade
    assert _grade(59.9) == "B"


def test_grade_b_at_boundary():
    from intelligence.composite_scorer import _grade
    assert _grade(40.0) == "B"


def test_grade_c_just_below_b():
    from intelligence.composite_scorer import _grade
    assert _grade(39.9) == "C"


def test_grade_c_at_zero():
    from intelligence.composite_scorer import _grade
    assert _grade(0.0) == "C"


# ── compute_composite — no data ────────────────────────────────────────────────

async def test_returns_zero_when_no_factor_scores(db_session, db_engine):
    from intelligence.composite_scorer import compute_composite
    result = await compute_composite("AAPL")
    assert result == {"score": 0.0, "grade": "C", "breakdown": {}}


# ── compute_composite — with data ─────────────────────────────────────────────

async def _seed_factors(db_engine, ticker: str, rows: list[dict]) -> None:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        for r in rows:
            session.add(FactorScore(
                ticker=ticker,
                name=r["name"],
                bucket=r["bucket"],
                ic=r["ic"],
                status=r["status"],
                computed_at=datetime.now(UTC),
            ))
        await session.commit()


async def test_score_scales_with_ic(db_session, db_engine):
    """IC=0.10 in every factor → composite=100, grade=S."""
    from intelligence.composite_scorer import compute_composite
    await _seed_factors(db_engine, "NVDA", [
        {"name": "ret_1m",           "bucket": "momentum",   "ic": 0.10, "status": "alive"},
        {"name": "ret_3m",           "bucket": "momentum",   "ic": 0.10, "status": "alive"},
        {"name": "ret_6m",           "bucket": "momentum",   "ic": 0.10, "status": "alive"},
        {"name": "ret_12m",          "bucket": "momentum",   "ic": 0.10, "status": "alive"},
        {"name": "realized_vol_20d", "bucket": "volatility", "ic": 0.10, "status": "alive"},
        {"name": "realized_vol_60d", "bucket": "volatility", "ic": 0.10, "status": "alive"},
        {"name": "turnover_ratio",   "bucket": "liquidity",  "ic": 0.10, "status": "alive"},
        {"name": "ret_consistency",  "bucket": "quality",    "ic": 0.10, "status": "alive"},
    ])
    result = await compute_composite("NVDA")
    assert result["score"] == pytest.approx(100.0)
    assert result["grade"] == "S"


async def test_reversed_factors_penalize_score(db_session, db_engine):
    """Reversed factors (negative IC) penalize the score via signed IC."""
    from intelligence.composite_scorer import compute_composite
    await _seed_factors(db_engine, "TSLA", [
        {"name": "ret_1m",  "bucket": "momentum", "ic": -0.08, "status": "reversed"},
        {"name": "ret_3m",  "bucket": "momentum", "ic": -0.08, "status": "reversed"},
        {"name": "ret_6m",  "bucket": "momentum", "ic": -0.08, "status": "reversed"},
        {"name": "ret_12m", "bucket": "momentum", "ic": -0.08, "status": "reversed"},
    ])
    result = await compute_composite("TSLA")
    # Only momentum bucket → mean(IC) = -0.08 → -80, clamped to 0
    assert result["score"] == pytest.approx(0.0)
    assert result["grade"] == "C"
    assert "momentum" in result["breakdown"]
    assert result["breakdown"]["momentum"] == pytest.approx(0.0)


async def test_dead_factors_lower_score(db_session, db_engine):
    """Dead factors (zero IC) drag the bucket score down via signed IC."""
    from intelligence.composite_scorer import compute_composite
    await _seed_factors(db_engine, "MSFT", [
        {"name": "ret_1m",  "bucket": "momentum", "ic": 0.10, "status": "alive"},
        {"name": "ret_3m",  "bucket": "momentum", "ic": 0.00, "status": "dead"},
        {"name": "ret_6m",  "bucket": "momentum", "ic": 0.00, "status": "dead"},
        {"name": "ret_12m", "bucket": "momentum", "ic": 0.00, "status": "dead"},
    ])
    result = await compute_composite("MSFT")
    # mean(IC) = (0.10+0+0+0)/4 = 0.025 → 25 pts → grade C
    assert result["score"] == pytest.approx(25.0)
    assert result["grade"] == "C"


async def test_breakdown_contains_all_populated_buckets(db_session, db_engine):
    """Breakdown dict should have one key per bucket that has data."""
    from intelligence.composite_scorer import compute_composite
    await _seed_factors(db_engine, "AMZN", [
        {"name": "ret_1m",           "bucket": "momentum",   "ic": 0.06, "status": "alive"},
        {"name": "ret_3m",           "bucket": "momentum",   "ic": 0.06, "status": "alive"},
        {"name": "ret_6m",           "bucket": "momentum",   "ic": 0.06, "status": "alive"},
        {"name": "ret_12m",          "bucket": "momentum",   "ic": 0.06, "status": "alive"},
        {"name": "realized_vol_20d", "bucket": "volatility", "ic": 0.04, "status": "dead"},
        {"name": "realized_vol_60d", "bucket": "volatility", "ic": 0.04, "status": "dead"},
    ])
    result = await compute_composite("AMZN")
    assert set(result["breakdown"].keys()) == {"momentum", "volatility"}
    assert result["breakdown"]["momentum"] == pytest.approx(60.0)
    assert result["breakdown"]["volatility"] == pytest.approx(40.0)


async def test_score_is_capped_at_100(db_session, db_engine):
    """Extremely high IC values should not push score above 100."""
    from intelligence.composite_scorer import compute_composite
    await _seed_factors(db_engine, "META", [
        {"name": "ret_1m", "bucket": "momentum", "ic": 0.99, "status": "alive"},
    ])
    result = await compute_composite("META")
    assert result["score"] <= 100.0
