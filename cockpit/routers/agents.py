"""Agent status endpoints."""

from sqlalchemy import select

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from cockpit.schemas import AgentStatus, LogEntry
from memory.database import AgentLog, get_session

router = APIRouter()

_KNOWN_AGENTS = [
    "orchestrator",
    "news_hunter",
    "market_watch",
    "sentiment_analyst",
    "research_analyst",
    "risk_monitor",
]


@router.get("", response_model=list[AgentStatus])
async def list_agents(session: AsyncSession = Depends(get_session)) -> list[AgentStatus]:
    """Return the latest status for every known agent."""
    result = []
    for name in _KNOWN_AGENTS:
        row = (
            await session.execute(
                select(AgentLog)
                .where(AgentLog.agent_name == name)
                .order_by(AgentLog.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        result.append(AgentStatus(
            name=name,
            last_action=row.action if row else None,
            last_message=row.message if row else None,
            last_seen=row.created_at if row else None,
            level=row.level if row else "info",
        ))
    return result


@router.get("/{name}/logs", response_model=list[LogEntry])
async def agent_logs(
    name: str,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> list[LogEntry]:
    """Return the most recent logs for a specific agent."""
    rows = (
        await session.execute(
            select(AgentLog)
            .where(AgentLog.agent_name == name)
            .order_by(AgentLog.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        LogEntry(
            id=r.id,
            agent_name=r.agent_name,
            action=r.action,
            message=r.message,
            level=r.level,
            created_at=r.created_at,
        )
        for r in rows
    ]
