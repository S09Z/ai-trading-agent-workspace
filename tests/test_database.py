"""Tests for SQLAlchemy models against a real PostgreSQL instance."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from memory.database import AgentLog, Article, MarketSnapshot, Signal

# ── Article ────────────────────────────────────────────────────────────────────

async def test_article_create_and_read(db_session):
    article = Article(
        title="NVDA Q4 earnings beat estimates",
        source="reuters",
        url="https://example.com/nvda-q4",
        tickers=["NVDA"],
    )
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)

    result = await db_session.execute(select(Article).where(Article.id == article.id))
    fetched = result.scalar_one()

    assert fetched.title == "NVDA Q4 earnings beat estimates"
    assert fetched.source == "reuters"
    assert fetched.tickers == ["NVDA"]


async def test_article_default_fields(db_session):
    article = Article(title="Test", source="rss", url="https://example.com/defaults")
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)

    assert article.id is not None
    assert article.embedded is False
    assert article.sentiment is None
    assert article.sentiment_score is None
    assert article.collected_at is not None


async def test_article_url_uniqueness(db_session):
    url = "https://example.com/duplicate"
    db_session.add(Article(title="First", source="test", url=url))
    await db_session.commit()

    db_session.add(Article(title="Second", source="test", url=url))
    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


async def test_article_sentiment_update(db_session):
    article = Article(title="Fed raises rates", source="cnbc", url="https://example.com/fed")
    db_session.add(article)
    await db_session.commit()

    article.sentiment = "bearish"
    article.sentiment_score = -0.75
    article.embedded = True
    await db_session.commit()
    await db_session.refresh(article)

    assert article.sentiment == "bearish"
    assert article.sentiment_score == pytest.approx(-0.75)
    assert article.embedded is True


async def test_article_multi_ticker(db_session):
    article = Article(
        title="Tech rally: AAPL, MSFT, NVDA all up",
        source="bloomberg",
        url="https://example.com/tech-rally",
        tickers=["AAPL", "MSFT", "NVDA"],
    )
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)

    assert len(article.tickers) == 3
    assert "MSFT" in article.tickers


# ── Signal ─────────────────────────────────────────────────────────────────────

async def test_signal_create(db_session):
    signal = Signal(
        ticker="TSLA",
        signal_type="bullish",
        confidence=0.82,
        source_agent="sentiment_analyst",
        rationale="Strong positive sentiment across 12 articles.",
    )
    db_session.add(signal)
    await db_session.commit()
    await db_session.refresh(signal)

    assert signal.id is not None
    assert signal.ticker == "TSLA"
    assert signal.confidence == pytest.approx(0.82)
    assert signal.created_at is not None


async def test_signal_default_meta(db_session):
    signal = Signal(
        ticker="SPY", signal_type="watchlist", confidence=0.5, source_agent="risk_monitor"
    )
    db_session.add(signal)
    await db_session.commit()
    await db_session.refresh(signal)

    assert signal.meta == {}


# ── AgentLog ───────────────────────────────────────────────────────────────────

async def test_agent_log_create(db_session):
    log = AgentLog(
        agent_name="news_hunter",
        action="fetch_rss",
        message="Collected 5 new articles from Reuters.",
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    assert log.id is not None
    assert log.level == "info"
    assert log.created_at is not None


async def test_agent_log_query_by_agent(db_session):
    for i in range(3):
        db_session.add(AgentLog(agent_name="market_watch", action="poll", message=f"Tick {i}"))
    db_session.add(AgentLog(agent_name="orchestrator", action="route", message="Routed task"))
    await db_session.commit()

    result = await db_session.execute(
        select(AgentLog).where(AgentLog.agent_name == "market_watch")
    )
    logs = result.scalars().all()

    assert len(logs) == 3


# ── MarketSnapshot ─────────────────────────────────────────────────────────────

async def test_market_snapshot_create(db_session):
    ts = datetime(2024, 1, 15, 14, 30, tzinfo=UTC)
    snap = MarketSnapshot(
        ticker="AAPL", timestamp=ts,
        open=185.0, high=187.5, low=184.2, close=186.8, volume=52_000_000,
    )
    db_session.add(snap)
    await db_session.commit()

    result = await db_session.execute(
        select(MarketSnapshot).where(MarketSnapshot.ticker == "AAPL")
    )
    fetched = result.scalar_one()

    assert fetched.close == pytest.approx(186.8)
    assert fetched.volume == pytest.approx(52_000_000)


async def test_market_snapshot_composite_pk(db_session):
    """Different timestamps for the same ticker are distinct rows."""
    ts1 = datetime(2024, 1, 15, 14, 30, tzinfo=UTC)
    ts2 = datetime(2024, 1, 15, 14, 31, tzinfo=UTC)
    db_session.add(MarketSnapshot(
        ticker="SPY", timestamp=ts1,
        open=470.0, high=471.0, low=469.5, close=470.5, volume=10_000_000,
    ))
    db_session.add(MarketSnapshot(
        ticker="SPY", timestamp=ts2,
        open=470.5, high=472.0, low=470.0, close=471.8, volume=11_000_000,
    ))
    await db_session.commit()

    result = await db_session.execute(
        select(MarketSnapshot).where(MarketSnapshot.ticker == "SPY")
    )
    rows = result.scalars().all()
    assert len(rows) == 2
