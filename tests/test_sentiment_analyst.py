"""Tests for SentimentAnalystAgent — real DB, mocked sentiment classifier."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from memory.database import AgentLog, Article, Signal


def _article(n: int = 0, tickers: list | None = None) -> Article:
    return Article(
        title=f"Article {n}",
        source="test",
        url=f"https://example.com/a{n}",
        tickers=tickers or [],
    )


# ── core behaviour ─────────────────────────────────────────────────────────────

async def test_run_updates_article_sentiment(db_session, db_engine):
    from agents.sentiment_analyst import SentimentAnalystAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(_article(0))
        await s.commit()

    with patch("agents.sentiment_analyst.analyze_sentiment",
               new=AsyncMock(return_value={"sentiment": "bullish", "score": 0.8})):
        await SentimentAnalystAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        art = (await s.execute(select(Article))).scalars().first()

    assert art.sentiment == "bullish"
    assert art.sentiment_score == pytest.approx(0.8)


async def test_run_skips_already_analyzed_articles(db_session, db_engine):
    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        art = _article(0)
        art.sentiment = "neutral"
        art.sentiment_score = 0.0
        s.add(art)
        await s.commit()

    with patch("agents.sentiment_analyst.analyze_sentiment",
               new=AsyncMock(return_value={"sentiment": "bullish", "score": 0.9})) as mock_fn:
        from agents.sentiment_analyst import SentimentAnalystAgent
        await SentimentAnalystAgent().run()

    mock_fn.assert_not_called()


async def test_run_creates_bullish_signal_above_threshold(db_session, db_engine):
    from agents.sentiment_analyst import SentimentAnalystAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(_article(0, tickers=["NVDA"]))
        await s.commit()

    with patch("agents.sentiment_analyst.analyze_sentiment",
               new=AsyncMock(return_value={"sentiment": "bullish", "score": 0.9})):
        await SentimentAnalystAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        signals = (await s.execute(
            select(Signal).where(Signal.ticker == "NVDA", Signal.signal_type == "bullish")
        )).scalars().all()

    assert len(signals) == 1
    assert signals[0].source_agent == "sentiment_analyst"


async def test_run_creates_bearish_signal_below_threshold(db_session, db_engine):
    from agents.sentiment_analyst import SentimentAnalystAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(_article(0, tickers=["TSLA"]))
        await s.commit()

    with patch("agents.sentiment_analyst.analyze_sentiment",
               new=AsyncMock(return_value={"sentiment": "bearish", "score": -0.8})):
        await SentimentAnalystAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        signals = (await s.execute(
            select(Signal).where(Signal.ticker == "TSLA", Signal.signal_type == "bearish")
        )).scalars().all()

    assert len(signals) == 1


async def test_run_skips_signal_for_neutral_score(db_session, db_engine):
    from agents.sentiment_analyst import SentimentAnalystAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(_article(0, tickers=["AAPL"]))
        await s.commit()

    with patch("agents.sentiment_analyst.analyze_sentiment",
               new=AsyncMock(return_value={"sentiment": "neutral", "score": 0.1})):
        await SentimentAnalystAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        signals = (await s.execute(select(Signal))).scalars().all()

    assert signals == []


async def test_run_creates_signal_with_grades(db_session, db_engine):
    from agents.sentiment_analyst import SentimentAnalystAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(_article(0, tickers=["AAPL"]))
        await s.commit()

    with patch("agents.sentiment_analyst.analyze_sentiment",
               new=AsyncMock(return_value={"sentiment": "bullish", "score": 0.85})):
        await SentimentAnalystAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        sig = (await s.execute(
            select(Signal).where(Signal.ticker == "AAPL")
        )).scalars().first()

    assert sig.grade_short == "S"
    assert sig.grade_mid == "A"
    assert sig.grade_long == "B"


def test_grades_bullish_high_confidence():
    from agents.sentiment_analyst import _grades
    assert _grades("bullish", 0.85) == ("S", "A", "B")


def test_grades_bullish_moderate_confidence():
    from agents.sentiment_analyst import _grades
    assert _grades("bullish", 0.70) == ("A", "B", "B")


def test_grades_bearish_high_confidence():
    from agents.sentiment_analyst import _grades
    gs, gm, gl = _grades("bearish", 0.85)
    assert gs == "C"
    assert gm == "C"
    assert gl == "B"


def test_grades_bearish_moderate_confidence():
    from agents.sentiment_analyst import _grades
    gs, gm, gl = _grades("bearish", 0.70)
    assert gs == "C"
    assert gm == "B"


def test_grades_watchlist_is_hold():
    from agents.sentiment_analyst import _grades
    assert _grades("watchlist", 0.5) == ("B", "B", "B")


async def test_run_writes_agent_log(db_session, db_engine):
    from agents.sentiment_analyst import SentimentAnalystAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(_article(0))
        await s.commit()

    with patch("agents.sentiment_analyst.analyze_sentiment",
               new=AsyncMock(return_value={"sentiment": "neutral", "score": 0.0})):
        await SentimentAnalystAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        logs = (await s.execute(
            select(AgentLog).where(AgentLog.agent_name == "sentiment_analyst")
        )).scalars().all()

    assert len(logs) >= 1
