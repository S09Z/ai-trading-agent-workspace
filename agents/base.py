import asyncio
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from memory.database import AgentLog, AsyncSessionLocal


class BaseAgent(ABC):
    name: str = "base"

    async def log(
        self,
        action: str,
        message: str,
        level: str = "info",
        meta: dict | None = None,
    ) -> None:
        """Append an entry to AgentLog — the source of truth for the Virtual Office UI."""
        async with AsyncSessionLocal() as session:
            session.add(AgentLog(
                agent_name=self.name,
                action=action,
                message=message,
                level=level,
                meta=meta or {},
            ))
            await session.commit()

    async def is_halted(self) -> bool:
        """Return True if the circuit breaker is open (RiskMonitor fired recently)."""
        cutoff = datetime.now(UTC) - timedelta(minutes=15)
        async with AsyncSessionLocal() as session:
            count = (
                await session.execute(
                    select(func.count()).select_from(AgentLog).where(
                        AgentLog.action == "circuit_breaker",
                        AgentLog.created_at >= cutoff,
                    )
                )
            ).scalar() or 0
        return count > 0

    @abstractmethod
    async def run(self) -> None:
        """Single execution cycle. Override in each agent."""
        ...

    async def run_forever(self, interval: int) -> None:
        """Run in a loop, sleeping `interval` seconds between cycles.
        Errors are caught, logged, and the loop continues.
        """
        while True:
            try:
                await self.run()
            except Exception as exc:
                await self.log("error", str(exc), level="error")
            await asyncio.sleep(interval)
