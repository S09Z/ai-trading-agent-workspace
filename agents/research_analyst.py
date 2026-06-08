import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from agents.base import BaseAgent
from config.settings import get_settings
from memory.database import AsyncSessionLocal, Signal
from memory.vector_store import search

_settings = get_settings()

_SYSTEM = "You are a senior equity analyst. Be concise and direct."

_VALID_GRADES = {"S", "A", "B", "C"}


def _parse_grades(text: str) -> tuple[str | None, str | None, str | None]:
    """Extract SHORT/MID/LONG grades from LLM response text."""
    def _find(label: str) -> str | None:
        m = re.search(rf"{label}[:\s]+([SABC])", text, re.IGNORECASE)
        return m.group(1).upper() if m and m.group(1).upper() in _VALID_GRADES else None
    return _find("SHORT"), _find("MID"), _find("LONG")


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

        news_context = "\n".join(f"- {d.get('title', '')}" for d in docs if d.get("title"))

        # Pull past signal outcomes for this ticker from memory
        memory_docs = await search(f"{target} signal outcome correct incorrect", limit=4)
        memory_lines = [
            d["outcome_summary"]
            for d in memory_docs
            if d.get("type") == "signal_outcome" and d.get("ticker") == target
        ]
        memory_section = (
            "\n\nPast signal outcomes:\n" + "\n".join(f"- {l}" for l in memory_lines)
            if memory_lines else ""
        )

        prompt = (
            f"Ticker: {target}\n\nRecent news:\n{news_context}{memory_section}\n\n"
            "Write a 3-sentence investment thesis: directional bias, key risk, near-term catalyst.\n\n"
            "Then grade the outlook for each time horizon (S=Strong Buy, A=Buy, B=Hold, C=Sell):\n"
            "SHORT: <grade>\n"
            "MID: <grade>\n"
            "LONG: <grade>"
        )

        from intelligence.llm import analyze
        analysis = await analyze(prompt, system=_SYSTEM, max_tokens=200)

        gs, gm, gl = _parse_grades(analysis)

        async with AsyncSessionLocal() as session:
            session.add(Signal(
                ticker=target,
                signal_type="watchlist",
                confidence=0.5,
                source_agent=self.name,
                rationale=analysis[:500],
                grade_short=gs,
                grade_mid=gm,
                grade_long=gl,
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
