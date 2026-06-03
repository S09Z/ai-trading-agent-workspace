"""Tests for NewsHunterAgent.

Uses real PostgreSQL (db_session for cleanup) and mocks fetch_all + vector_store.upsert.
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from memory.database import AgentLog, Article


def _articles(n: int = 2) -> list[dict]:
    return [
        {
            "title": f"Article {i}",
            "content": f"Content {i}",
            "source": "reuters",
            "url": f"https://reuters.com/article-{i}",
            "published_at": None,
            "tickers": ["NVDA"] if i == 0 else [],
        }
        for i in range(n)
    ]


@pytest.fixture
def mock_fetch_all():
    with patch("agents.news_hunter.fetch_all", new=AsyncMock(return_value=_articles(2))):
        yield


@pytest.fixture
def mock_upsert():
    with patch("agents.news_hunter.upsert", new=AsyncMock()):
        yield


# ── tests ──────────────────────────────────────────────────────────────────────

async def test_run_stores_new_articles(db_session, db_engine, mock_fetch_all, mock_upsert):
    from agents.news_hunter import NewsHunterAgent

    await NewsHunterAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        rows = (await s.execute(select(Article))).scalars().all()

    assert len(rows) == 2
    urls = {r.url for r in rows}
    assert "https://reuters.com/article-0" in urls
    assert "https://reuters.com/article-1" in urls


async def test_run_skips_duplicate_url(db_session, db_engine, mock_upsert):
    from agents.news_hunter import NewsHunterAgent

    same = _articles(1)  # one article

    # Run twice with the same article
    with patch("agents.news_hunter.fetch_all", new=AsyncMock(return_value=same)):
        await NewsHunterAgent().run()
    with patch("agents.news_hunter.fetch_all", new=AsyncMock(return_value=same)):
        await NewsHunterAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        rows = (await s.execute(select(Article))).scalars().all()

    assert len(rows) == 1  # no duplicate


async def test_run_embeds_articles(db_session, mock_fetch_all):
    from agents.news_hunter import NewsHunterAgent

    with patch("agents.news_hunter.upsert", new=AsyncMock()) as mock_upsert:
        await NewsHunterAgent().run()

    assert mock_upsert.call_count == 2


async def test_run_marks_articles_as_embedded(db_session, db_engine, mock_fetch_all, mock_upsert):
    from agents.news_hunter import NewsHunterAgent

    await NewsHunterAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        rows = (await s.execute(select(Article))).scalars().all()

    assert all(r.embedded for r in rows)


async def test_run_writes_agent_log(db_session, db_engine, mock_fetch_all, mock_upsert):
    from agents.news_hunter import NewsHunterAgent

    await NewsHunterAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        logs = (
            await s.execute(select(AgentLog).where(AgentLog.agent_name == "news_hunter"))
        ).scalars().all()

    assert len(logs) >= 1
    assert any("2" in log.message for log in logs)  # "2 new articles"


async def test_run_no_articles_when_fetch_empty(db_session, db_engine, mock_upsert):
    from agents.news_hunter import NewsHunterAgent

    with patch("agents.news_hunter.fetch_all", new=AsyncMock(return_value=[])):
        await NewsHunterAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        rows = (await s.execute(select(Article))).scalars().all()

    assert rows == []
