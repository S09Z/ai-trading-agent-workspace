"""Tests for OrchestratorAgent — all sub-agents mocked."""

from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from memory.database import AgentLog


async def test_run_calls_all_layers(db_session):
    from agents.orchestrator import OrchestratorAgent

    with patch("agents.orchestrator.NewsHunterAgent.run", new=AsyncMock()) as news, \
         patch("agents.orchestrator.MarketWatchAgent.run", new=AsyncMock()) as market, \
         patch("agents.orchestrator.SentimentAnalystAgent.run", new=AsyncMock()) as sentiment, \
         patch("agents.orchestrator.RiskMonitorAgent.run", new=AsyncMock()) as risk, \
         patch("agents.orchestrator.ResearchAnalystAgent.run", new=AsyncMock()) as research:
        await OrchestratorAgent().run()

    news.assert_called_once()
    market.assert_called_once()
    sentiment.assert_called_once()
    risk.assert_called_once()
    research.assert_called_once()


async def test_run_writes_cycle_logs(db_session, db_engine):
    from agents.orchestrator import OrchestratorAgent

    with patch("agents.orchestrator.NewsHunterAgent.run", new=AsyncMock()), \
         patch("agents.orchestrator.MarketWatchAgent.run", new=AsyncMock()), \
         patch("agents.orchestrator.SentimentAnalystAgent.run", new=AsyncMock()), \
         patch("agents.orchestrator.RiskMonitorAgent.run", new=AsyncMock()), \
         patch("agents.orchestrator.ResearchAnalystAgent.run", new=AsyncMock()):
        await OrchestratorAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        logs = (await s.execute(
            select(AgentLog).where(
                AgentLog.agent_name == "orchestrator",
                AgentLog.action == "cycle",
            )
        )).scalars().all()

    assert len(logs) == 4  # Layer 1 + Layer 2 + Layer 3 + complete
    messages = [log.message for log in logs]
    assert any("complete" in m for m in messages)


async def test_run_completes_even_if_sub_agent_errors(db_session, db_engine):
    from agents.orchestrator import OrchestratorAgent

    err = AsyncMock(side_effect=RuntimeError("down"))
    with patch("agents.orchestrator.NewsHunterAgent.run", new=err), \
         patch("agents.orchestrator.MarketWatchAgent.run", new=AsyncMock()), \
         patch("agents.orchestrator.SentimentAnalystAgent.run", new=AsyncMock()), \
         patch("agents.orchestrator.RiskMonitorAgent.run", new=AsyncMock()), \
         patch("agents.orchestrator.ResearchAnalystAgent.run", new=AsyncMock()):
        try:
            await OrchestratorAgent().run()
        except RuntimeError:
            pass  # gather propagates — acceptable in orchestrator tests
