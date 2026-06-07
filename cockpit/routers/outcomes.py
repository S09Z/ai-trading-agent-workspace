"""Signal outcome endpoints — accuracy tracking for agent memory."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cockpit.schemas import AgentAccuracy, SignalOutcomeOut
from memory.database import SignalOutcome, get_session

router = APIRouter()


@router.get("", response_model=list[SignalOutcomeOut])
async def list_outcomes(
    limit: int = 20,
    ticker: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[SignalOutcomeOut]:
    """Recent signal outcomes, newest first."""
    q = select(SignalOutcome).order_by(SignalOutcome.created_at.desc()).limit(limit)
    if ticker:
        q = q.where(SignalOutcome.ticker == ticker.upper())
    rows = (await session.execute(q)).scalars().all()
    return [_to_schema(r) for r in rows]


@router.get("/accuracy", response_model=list[AgentAccuracy])
async def agent_accuracy(
    session: AsyncSession = Depends(get_session),
) -> list[AgentAccuracy]:
    """Per-agent accuracy stats based on 5-day outcome labels."""
    rows = (
        await session.execute(
            select(
                SignalOutcome.source_agent,
                SignalOutcome.outcome_5d,
                func.count().label("cnt"),
            )
            .where(SignalOutcome.outcome_5d.isnot(None))
            .group_by(SignalOutcome.source_agent, SignalOutcome.outcome_5d)
        )
    ).all()

    # Aggregate by agent
    stats: dict[str, dict[str, int]] = {}
    for agent, outcome, cnt in rows:
        s = stats.setdefault(agent, {"correct": 0, "incorrect": 0, "neutral": 0})
        if outcome in s:
            s[outcome] += cnt

    result = []
    for agent, s in sorted(stats.items()):
        total = s["correct"] + s["incorrect"] + s["neutral"]
        directional = s["correct"] + s["incorrect"]
        result.append(AgentAccuracy(
            agent=agent,
            total=total,
            correct=s["correct"],
            incorrect=s["incorrect"],
            neutral=s["neutral"],
            accuracy_pct=round(s["correct"] / directional * 100, 1) if directional else None,
        ))
    return result


def _to_schema(r: SignalOutcome) -> SignalOutcomeOut:
    change_pct = None
    if r.price_at_signal and r.price_5d:
        change_pct = round((r.price_5d - r.price_at_signal) / r.price_at_signal * 100, 2)
    return SignalOutcomeOut(
        id=r.id,
        signal_id=r.signal_id,
        ticker=r.ticker,
        signal_type=r.signal_type,
        source_agent=r.source_agent,
        price_at_signal=r.price_at_signal,
        price_5d=r.price_5d,
        outcome_5d=r.outcome_5d,
        change_pct_5d=change_pct,
        created_at=r.created_at,
        evaluated_at=r.evaluated_at,
    )
