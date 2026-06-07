"""Tests for MemoryAgent — real DB, mocked yfinance + Qdrant."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from memory.database import AgentLog, Signal, SignalOutcome


def _signal(ticker: str, signal_type: str, days_ago: int = 2, source: str = "sentiment_analyst"):
    return Signal(
        ticker=ticker,
        signal_type=signal_type,
        confidence=0.75,
        source_agent=source,
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
    )


async def test_skips_when_no_signals(db_session, db_engine):
    from sqlalchemy import delete

    from agents.memory_agent import MemoryAgent

    # Pre-clean: conftest only deletes AFTER each test, not before
    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        await s.execute(delete(SignalOutcome))
        await s.execute(delete(Signal))
        await s.commit()

    with patch("agents.memory_agent.upsert", new=AsyncMock()):
        await MemoryAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        outcomes = (await s.execute(select(SignalOutcome))).scalars().all()
    assert outcomes == []


async def test_creates_outcome_for_old_bullish_signal(db_session, db_engine):
    from agents.memory_agent import MemoryAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(_signal("AAPL", "bullish", days_ago=6))
        await s.commit()

    # price at signal: 180, price 5d later: 194 → +7.8% → correct
    prices = {"AAPL": iter([180.0, 182.0, 194.0, None])}

    def fake_fetch(ticker, on_date):
        return next(prices[ticker], None)

    with patch("agents.memory_agent._fetch_close", side_effect=fake_fetch), \
         patch("agents.memory_agent.upsert", new=AsyncMock()):
        await MemoryAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        outcomes = (await s.execute(select(SignalOutcome))).scalars().all()

    assert len(outcomes) == 1
    assert outcomes[0].ticker == "AAPL"
    assert outcomes[0].outcome_5d == "correct"
    assert outcomes[0].price_at_signal == 180.0
    assert outcomes[0].price_5d == 194.0


async def test_bearish_signal_down_is_correct(db_session, db_engine):
    from agents.memory_agent import MemoryAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(_signal("TSLA", "bearish", days_ago=6))
        await s.commit()

    # price drops: 250 → 240 → correct bearish
    prices = {"TSLA": iter([250.0, 248.0, 240.0, None])}

    def fake_fetch(ticker, on_date):
        return next(prices[ticker], None)

    with patch("agents.memory_agent._fetch_close", side_effect=fake_fetch), \
         patch("agents.memory_agent.upsert", new=AsyncMock()):
        await MemoryAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        outcomes = (await s.execute(select(SignalOutcome))).scalars().all()

    assert outcomes[0].outcome_5d == "correct"


async def test_bullish_signal_down_is_incorrect(db_session, db_engine):
    from agents.memory_agent import MemoryAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(_signal("NVDA", "bullish", days_ago=6))
        await s.commit()

    prices = {"NVDA": iter([500.0, 498.0, 490.0, None])}

    def fake_fetch(ticker, on_date):
        return next(prices[ticker], None)

    with patch("agents.memory_agent._fetch_close", side_effect=fake_fetch), \
         patch("agents.memory_agent.upsert", new=AsyncMock()):
        await MemoryAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        outcomes = (await s.execute(select(SignalOutcome))).scalars().all()

    assert outcomes[0].outcome_5d == "incorrect"


async def test_skips_signal_newer_than_1_day(db_session, db_engine):
    from agents.memory_agent import MemoryAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(_signal("AAPL", "bullish", days_ago=0))  # just created
        await s.commit()

    with patch("agents.memory_agent.upsert", new=AsyncMock()):
        await MemoryAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        outcomes = (await s.execute(select(SignalOutcome))).scalars().all()

    assert outcomes == []


async def test_does_not_double_evaluate(db_session, db_engine):
    from agents.memory_agent import MemoryAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        sig = _signal("AAPL", "bullish", days_ago=6)
        s.add(sig)
        await s.commit()
        await s.refresh(sig)
        s.add(SignalOutcome(
            signal_id=sig.id,
            ticker="AAPL",
            signal_type="bullish",
            source_agent="sentiment_analyst",
            outcome_5d="correct",
        ))
        await s.commit()

    with patch("agents.memory_agent.upsert", new=AsyncMock()):
        await MemoryAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        outcomes = (await s.execute(select(SignalOutcome))).scalars().all()

    assert len(outcomes) == 1  # not doubled


async def test_embeds_outcome_into_qdrant_when_5d_known(db_session, db_engine):
    from agents.memory_agent import MemoryAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(_signal("MSFT", "bullish", days_ago=6))
        await s.commit()

    prices = {"MSFT": iter([400.0, 402.0, 420.0, None])}

    def fake_fetch(ticker, on_date):
        return next(prices[ticker], None)

    mock_upsert = AsyncMock()
    with patch("agents.memory_agent._fetch_close", side_effect=fake_fetch), \
         patch("agents.memory_agent.upsert", new=mock_upsert):
        await MemoryAgent().run()

    mock_upsert.assert_called_once()
    call_kwargs = mock_upsert.call_args
    payload = call_kwargs.kwargs.get("payload") or call_kwargs.args[2]
    assert payload["type"] == "signal_outcome"
    assert payload["ticker"] == "MSFT"
    assert payload["outcome"] == "correct"


async def test_writes_agent_log(db_session, db_engine):
    from agents.memory_agent import MemoryAgent

    with patch("agents.memory_agent.upsert", new=AsyncMock()):
        await MemoryAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        logs = (await s.execute(
            select(AgentLog).where(AgentLog.agent_name == "memory_agent")
        )).scalars().all()

    assert any(log.action == "evaluate" for log in logs)
