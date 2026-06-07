"""Tests for ResearchAnalystAgent — real DB, mocked RAG + LLM."""

from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from memory.database import AgentLog, Signal


async def test_run_skips_when_no_ticker_and_no_signals(db_session, db_engine):
    from agents.research_analyst import ResearchAnalystAgent

    with patch("agents.research_analyst.search", new=AsyncMock(return_value=[])):
        await ResearchAnalystAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        signals = (await s.execute(select(Signal))).scalars().all()

    assert signals == []


async def test_run_creates_signal_for_given_ticker(db_session, db_engine):
    from agents.research_analyst import ResearchAnalystAgent

    docs = [{"title": "NVDA GPU demand surges"}, {"title": "NVDA beats Q4 estimates"}]

    with patch("agents.research_analyst.search", new=AsyncMock(return_value=docs)), \
         patch("agents.research_analyst._settings") as s:
        s.use_local_llm = False
        mock_analyze = AsyncMock(return_value="Bullish thesis.")
        with patch("intelligence.claude_client.analyze", new=mock_analyze):
            await ResearchAnalystAgent().run(ticker="NVDA")

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        signals = (await s.execute(
            select(Signal).where(Signal.ticker == "NVDA")
        )).scalars().all()

    assert len(signals) == 1
    assert signals[0].signal_type == "watchlist"
    assert signals[0].source_agent == "research_analyst"


async def test_run_skips_when_no_rag_context(db_session, db_engine):
    from agents.research_analyst import ResearchAnalystAgent

    with patch("agents.research_analyst.search", new=AsyncMock(return_value=[])):
        await ResearchAnalystAgent().run(ticker="AAPL")

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        signals = (await s.execute(select(Signal))).scalars().all()

    assert signals == []


async def test_find_hot_ticker_returns_most_signaled(db_session, db_engine):
    from agents.research_analyst import ResearchAnalystAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        for _ in range(3):
            s.add(Signal(ticker="NVDA", signal_type="bullish", confidence=0.8,
                         source_agent="sentiment_analyst"))
        s.add(Signal(ticker="TSLA", signal_type="bullish", confidence=0.7,
                     source_agent="sentiment_analyst"))
        await s.commit()

    result = await ResearchAnalystAgent()._find_hot_ticker()
    assert result == "NVDA"


def test_parse_grades_full_response():
    from agents.research_analyst import _parse_grades
    text = "Bullish thesis.\nSHORT: S\nMID: A\nLONG: B"
    assert _parse_grades(text) == ("S", "A", "B")


def test_parse_grades_sell():
    from agents.research_analyst import _parse_grades
    text = "Bearish view.\nSHORT: C\nMID: C\nLONG: B"
    assert _parse_grades(text) == ("C", "C", "B")


def test_parse_grades_missing_returns_none():
    from agents.research_analyst import _parse_grades
    assert _parse_grades("No grades in this response.") == (None, None, None)


def test_parse_grades_case_insensitive():
    from agents.research_analyst import _parse_grades
    text = "short: a\nmid: b\nlong: s"
    assert _parse_grades(text) == ("A", "B", "S")


async def test_run_stores_grades_from_llm(db_session, db_engine):
    from agents.research_analyst import ResearchAnalystAgent

    docs = [{"title": "AAPL strong results"}]
    llm_response = "Strong bullish thesis.\nSHORT: S\nMID: A\nLONG: B"

    with patch("agents.research_analyst.search", new=AsyncMock(return_value=docs)), \
         patch("agents.research_analyst._settings") as s:
        s.use_local_llm = False
        with patch("intelligence.claude_client.analyze", new=AsyncMock(return_value=llm_response)):
            await ResearchAnalystAgent().run(ticker="AAPL")

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        sig = (await s.execute(
            select(Signal).where(Signal.ticker == "AAPL")
        )).scalars().first()

    assert sig.grade_short == "S"
    assert sig.grade_mid == "A"
    assert sig.grade_long == "B"


async def test_run_writes_agent_log(db_session, db_engine):
    from agents.research_analyst import ResearchAnalystAgent

    docs = [{"title": "AAPL strong iPhone sales"}]
    with patch("agents.research_analyst.search", new=AsyncMock(return_value=docs)), \
         patch("agents.research_analyst._settings") as s:
        s.use_local_llm = False
        with patch("intelligence.claude_client.analyze", new=AsyncMock(return_value="Thesis.")):
            await ResearchAnalystAgent().run(ticker="AAPL")

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        logs = (await s.execute(
            select(AgentLog).where(AgentLog.agent_name == "research_analyst")
        )).scalars().all()

    assert any(log.action == "research" for log in logs)
