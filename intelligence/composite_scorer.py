"""Composite alpha scorer — aggregates IC-weighted bucket scores into a 0–100 signal."""

from sqlalchemy import select

from agents.factor_library import ALPHA_BUCKETS
from memory.database import AsyncSessionLocal, FactorScore

# IC of 0.10 → 100 points; typical alive factor IC is 0.05–0.15
_IC_SCALE = 1000.0

_GRADE_THRESHOLDS: tuple[tuple[str, float], ...] = (
    ("S", 70.0),
    ("A", 50.0),
    ("B", 30.0),
    ("C",  0.0),
)


def _grade(score: float) -> str:
    for label, threshold in _GRADE_THRESHOLDS:
        if score >= threshold:
            return label
    return "C"


async def compute_composite(ticker: str) -> dict:
    """Aggregate FactorScore rows into a 0–100 composite score + S/A/B/C grade.

    Bucket score = mean |IC| × 1000 (dead factors drag naturally via low |IC|).
    Composite = mean of bucket scores, capped at 100.

    Returns {"score": 0.0, "grade": "C", "breakdown": {}} when no data exists.
    """
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(FactorScore).where(FactorScore.ticker == ticker)
        )).scalars().all()

    if not rows:
        return {"score": 0.0, "grade": "C", "breakdown": {}}

    by_bucket: dict[str, list[FactorScore]] = {b: [] for b in ALPHA_BUCKETS}
    for row in rows:
        if row.bucket in by_bucket:
            by_bucket[row.bucket].append(row)

    bucket_scores: dict[str, float] = {
        bucket: sum(abs(r.ic) for r in bucket_rows) / len(bucket_rows) * _IC_SCALE
        for bucket, bucket_rows in by_bucket.items()
        if bucket_rows
    }

    if not bucket_scores:
        return {"score": 0.0, "grade": "C", "breakdown": {}}

    composite = min(100.0, sum(bucket_scores.values()) / len(bucket_scores))
    breakdown = {k: round(v, 1) for k, v in bucket_scores.items()}

    return {"score": round(composite, 1), "grade": _grade(composite), "breakdown": breakdown}
