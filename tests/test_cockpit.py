"""Tests for the Agent Cockpit FastAPI endpoints."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from cockpit.app import app
from memory.database import AgentLog, Signal, get_session


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_engine):
    """AsyncClient wired to the app with the test DB session injected.

    Cleans all tables before AND after each test so tests are isolated
    regardless of production data or test ordering.
    """
    from memory.database import Base

    async def _clean():
        async with db_engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(table.delete())

    await _clean()

    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    await _clean()


# ── Health ─────────────────────────────────────────────────────────────────────

async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── GET /agents ────────────────────────────────────────────────────────────────

async def test_list_agents_returns_all_known(client):
    r = await client.get("/agents")
    assert r.status_code == 200
    names = [a["name"] for a in r.json()]
    assert "news_hunter" in names
    assert "sentiment_analyst" in names
    assert "risk_monitor" in names
    assert len(names) == 6


async def test_list_agents_null_when_no_logs(client):
    r = await client.get("/agents")
    agent = next(a for a in r.json() if a["name"] == "news_hunter")
    assert agent["last_action"] is None
    assert agent["last_seen"] is None


async def test_list_agents_reflects_latest_log(client, db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as s:
        s.add(AgentLog(agent_name="news_hunter", action="collect", message="Found 5 articles", level="info"))
        await s.commit()

    r = await client.get("/agents")
    agent = next(a for a in r.json() if a["name"] == "news_hunter")
    assert agent["last_action"] == "collect"
    assert agent["last_message"] == "Found 5 articles"


# ── GET /agents/{name}/logs ────────────────────────────────────────────────────

async def test_agent_logs_empty(client):
    r = await client.get("/agents/sentiment_analyst/logs")
    assert r.status_code == 200
    assert r.json() == []


async def test_agent_logs_returns_only_that_agent(client, db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as s:
        s.add(AgentLog(agent_name="sentiment_analyst", action="analyze", message="Done", level="info"))
        s.add(AgentLog(agent_name="risk_monitor", action="scan", message="OK", level="info"))
        await s.commit()

    r = await client.get("/agents/sentiment_analyst/logs")
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["agent_name"] == "sentiment_analyst"


async def test_agent_logs_respects_limit(client, db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as s:
        for i in range(5):
            s.add(AgentLog(agent_name="news_hunter", action="collect", message=f"run {i}", level="info"))
        await s.commit()

    r = await client.get("/agents/news_hunter/logs?limit=3")
    assert len(r.json()) == 3


# ── GET /signals ───────────────────────────────────────────────────────────────

async def test_signals_empty(client):
    r = await client.get("/signals")
    assert r.status_code == 200
    assert r.json() == []


async def test_signals_returns_recent(client, db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as s:
        s.add(Signal(ticker="AAPL", signal_type="bullish", confidence=0.8, source_agent="sentiment_analyst"))
        s.add(Signal(ticker="TSLA", signal_type="bearish", confidence=0.7, source_agent="sentiment_analyst"))
        await s.commit()

    r = await client.get("/signals")
    tickers = [s["ticker"] for s in r.json()]
    assert "AAPL" in tickers
    assert "TSLA" in tickers


async def test_signals_ordered_by_confidence(client, db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as s:
        s.add(Signal(ticker="LOW", signal_type="bullish", confidence=0.5, source_agent="sentiment_analyst"))
        s.add(Signal(ticker="HIGH", signal_type="bullish", confidence=0.9, source_agent="sentiment_analyst"))
        await s.commit()

    r = await client.get("/signals")
    signals = r.json()
    assert signals[0]["ticker"] == "HIGH"


# ── GET /logs ──────────────────────────────────────────────────────────────────

async def test_logs_empty(client):
    r = await client.get("/logs")
    assert r.status_code == 200
    assert r.json() == []


async def test_logs_returns_all_agents(client, db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as s:
        s.add(AgentLog(agent_name="news_hunter", action="collect", message="A", level="info"))
        s.add(AgentLog(agent_name="risk_monitor", action="scan", message="B", level="warning"))
        await s.commit()

    r = await client.get("/logs")
    names = {row["agent_name"] for row in r.json()}
    assert "news_hunter" in names
    assert "risk_monitor" in names
