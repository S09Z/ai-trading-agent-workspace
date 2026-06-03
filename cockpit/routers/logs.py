"""Activity log endpoints — REST + WebSocket streaming."""

import asyncio
import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cockpit.schemas import LogEntry
from memory.database import AgentLog, AsyncSessionLocal, get_session

router = APIRouter()

_WS_POLL_INTERVAL = 2  # seconds between DB polls


@router.get("", response_model=list[LogEntry])
async def list_logs(
    hours: int = 1,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> list[LogEntry]:
    """Return recent activity logs across all agents."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = (
        await session.execute(
            select(AgentLog)
            .where(AgentLog.created_at >= since)
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


@router.websocket("/ws")
async def stream_logs(websocket: WebSocket) -> None:
    """Stream new AgentLog rows to the client every 2 seconds."""
    await websocket.accept()
    last_id: int = await _latest_log_id()

    try:
        while True:
            await asyncio.sleep(_WS_POLL_INTERVAL)
            rows = await _logs_after(last_id)
            if rows:
                last_id = rows[-1].id
                for row in rows:
                    await websocket.send_text(json.dumps({
                        "id": row.id,
                        "agent_name": row.agent_name,
                        "action": row.action,
                        "message": row.message,
                        "level": row.level,
                        "created_at": row.created_at.isoformat(),
                    }))
    except WebSocketDisconnect:
        pass


async def _latest_log_id() -> int:
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                select(AgentLog.id).order_by(AgentLog.id.desc()).limit(1)
            )
        ).scalar_one_or_none()
    return row or 0


async def _logs_after(last_id: int) -> list[AgentLog]:
    async with AsyncSessionLocal() as session:
        return (
            await session.execute(
                select(AgentLog)
                .where(AgentLog.id > last_id)
                .order_by(AgentLog.id.asc())
            )
        ).scalars().all()
