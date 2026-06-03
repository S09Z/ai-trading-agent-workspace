import asyncio

from agents.base import BaseAgent
from agents.market_watch import MarketWatchAgent
from agents.news_hunter import NewsHunterAgent
from agents.research_analyst import ResearchAnalystAgent
from agents.risk_monitor import RiskMonitorAgent
from agents.sentiment_analyst import SentimentAnalystAgent


class OrchestratorAgent(BaseAgent):
    """Coordinates a full agent cycle in two parallel layers.

    Layer 1 (parallel): NewsHunter + MarketWatch — collect raw data
    Layer 2 (parallel): SentimentAnalyst + RiskMonitor — analyse and gate
    Layer 3 (sequential): ResearchAnalyst — deep dive on hottest ticker
    """

    name = "orchestrator"

    async def run(self) -> None:
        await self.log("cycle", "Layer 1 start — data collection")
        await asyncio.gather(
            NewsHunterAgent().run(),
            MarketWatchAgent().run(),
        )

        await self.log("cycle", "Layer 2 start — intelligence + risk")
        await asyncio.gather(
            SentimentAnalystAgent().run(),
            RiskMonitorAgent().run(),
        )

        await self.log("cycle", "Layer 3 start — research")
        await ResearchAnalystAgent().run()

        await self.log("cycle", "Full agent cycle complete")
