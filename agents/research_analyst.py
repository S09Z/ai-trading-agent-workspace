from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from agents.base import BaseAgent
from config.settings import get_settings
from memory.database import AsyncSessionLocal, Signal
from memory.vector_store import search

_settings = get_settings()

_SYSTEM = "You are a senior equity analyst. Be concise and direct."


class ResearchAnalystAgent(BaseAgent):
    name = "research_analyst"

    async def run(self, ticker: str | None = None) -> None:
        target = ticker or await self._find_hot_ticker()
        if not target:
            await self.log("scan", "No hot tickers found — skipping research cycle")
            return

        docs = await search(f"{target} earnings revenue forecast outlook", limit=8)
        if not docs:
            await self.log("research", f"No RAG context found for {target}")
            return

        context = "\n".join(f"- {d.get('title', '')}" for d in docs if d.get("title"))
        prompt = (
            f"Ticker: {target}\n\nRecent news:\n{context}\n\n"
            "Write a 3-sentence investment thesis: directional bias, key risk, near-term catalyst."
        )

        if _settings.use_local_llm:
            from intelligence.local_client import chat_local

            analysis = await chat_local(prompt, system=_SYSTEM, max_tokens=200)
        else:
            from intelligence.claude_client import analyze

            analysis = await analyze(prompt, max_tokens=200)

        async with AsyncSessionLocal() as session:
            session.add(Signal(
                ticker=target,
                signal_type="watchlist",
                confidence=0.5,
                source_agent=self.name,
                rationale=analysis[:500],
            ))
            await session.commit()

        await self.log("research", f"Research complete for {target}", meta={"ticker": target})

    async def _find_hot_ticker(self) -> str | None:
        """Return the ticker with most signals in the last 24h."""
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        async with AsyncSessionLocal() as session:
            row = (
                await session.execute(
                    select(Signal.ticker, func.count().label("cnt"))
                    .where(Signal.created_at >= cutoff, Signal.ticker != "MARKET")
                    .group_by(Signal.ticker)
                    .order_by(func.count().desc())
                    .limit(1)
                )
            ).first()
        return row[0] if row else None
