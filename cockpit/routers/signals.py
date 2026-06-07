"""Signal endpoints."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cockpit.schemas import SignalOut
from memory.database import Signal, get_session

router = APIRouter()


@router.get("", response_model=list[SignalOut])
async def list_signals(
    hours: int = 6,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
) -> list[SignalOut]:
    """Return recent signals ordered by confidence descending."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = (
        await session.execute(
            select(Signal)
            .where(Signal.created_at >= since)
            .order_by(Signal.confidence.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        SignalOut(
            id=r.id,
            ticker=r.ticker,
            signal_type=r.signal_type,
            confidence=r.confidence,
            source_agent=r.source_agent,
            rationale=r.rationale,
            grade_short=r.grade_short,
            grade_mid=r.grade_mid,
            grade_long=r.grade_long,
            created_at=r.created_at,
        )
        for r in rows
    ]
