from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from agents.base import BaseAgent
from memory.database import AgentLog, AsyncSessionLocal, Signal

SPIKE_WINDOW = 15          # minutes to look back
CIRCUIT_THRESHOLD = 3      # spike count that opens the circuit breaker


class RiskMonitorAgent(BaseAgent):
    name = "risk_monitor"

    async def _recent_spike_count(self) -> int:
        cutoff = datetime.now(UTC) - timedelta(minutes=SPIKE_WINDOW)
        async with AsyncSessionLocal() as session:
            return (
                await session.execute(
                    select(func.count()).select_from(AgentLog).where(
                        AgentLog.action == "spike_detected",
                        AgentLog.created_at >= cutoff,
                    )
                )
            ).scalar() or 0

    async def run(self) -> None:
        spike_count = await self._recent_spike_count()

        if spike_count >= CIRCUIT_THRESHOLD:
            await self.log(
                "circuit_breaker",
                f"Circuit OPEN — {spike_count} spikes in last {SPIKE_WINDOW}min, agents paused",
                level="warning",
                meta={"spike_count": spike_count, "window_minutes": SPIKE_WINDOW},
            )
            return

        if spike_count > 0:
            confidence = round(spike_count / CIRCUIT_THRESHOLD, 4)
            async with AsyncSessionLocal() as session:
                session.add(Signal(
                    ticker="MARKET",
                    signal_type="alert",
                    confidence=confidence,
                    source_agent=self.name,
                    rationale=f"{spike_count} price spike(s) in last {SPIKE_WINDOW}min",
                ))
                await session.commit()

        await self.log(
            "scan",
            f"Risk scan complete — spikes: {spike_count}/{CIRCUIT_THRESHOLD}",
            meta={"spike_count": spike_count},
        )
