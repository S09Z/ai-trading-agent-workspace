"""Tests for the /stocks endpoints — history (mocked yfinance) + analysis."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from cockpit.app import app
from cockpit.routers import stocks
from cockpit.schemas import StockBar, StockHistoryOut, StockMeta
from memory.database import Base, Signal, SignalOutcome, get_session


@pytest_asyncio.fixture
async def client(db_engine):
    """AsyncClient wired to the app with the test DB session injected."""

    async def _clean():
        async with db_engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(table.delete())

    await _clean()
    stocks._history_cache.clear()

    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    await _clean()


def _fake_history(ticker: str) -> StockHistoryOut:
    bars = [
        StockBar(t="2026-07-14", o=100.0, h=102.0, l=99.0, c=101.0, v=1_000_000),
        StockBar(t="2026-07-15", o=101.0, h=105.0, l=100.5, c=104.0, v=1_200_000),
    ]
    meta = StockMeta(
        ticker=ticker, name="Apple Inc.", market_cap=3e12, pe=30.0,
        price=104.0, change=3.0, change_pct=2.97, volume=1_200_000,
    )
    return StockHistoryOut(meta=meta, bars=bars)


# ── GET /stocks/{ticker}/history ────────────────────────────────────────────────

async def test_history_returns_bars_and_meta(client, monkeypatch):
    monkeypatch.setattr(stocks, "_fetch_history", _fake_history)

    r = await client.get("/stocks/aapl/history")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["ticker"] == "AAPL"
    assert body["meta"]["name"] == "Apple Inc."
    assert len(body["bars"]) == 2
    assert body["bars"][-1]["c"] == 104.0


async def test_history_is_cached(client, monkeypatch):
    calls = {"n": 0}

    def _counting(ticker: str) -> StockHistoryOut:
        calls["n"] += 1
        return _fake_history(ticker)

    monkeypatch.setattr(stocks, "_fetch_history", _counting)

    await client.get("/stocks/MSFT/history")
    await client.get("/stocks/MSFT/history")
    assert calls["n"] == 1  # second call served from TTL cache


# ── GET /stocks/{ticker}/analysis ───────────────────────────────────────────────

async def test_analysis_empty_state(client):
    r = await client.get("/stocks/NVDA/analysis")
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "NVDA"
    assert body["has_analysis"] is False
    assert body["composite_score"] is None
    assert body["outcomes"] == []


async def test_analysis_returns_composite(client, db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as s:
        sig = Signal(
            ticker="AAPL", signal_type="bullish", confidence=0.8,
            source_agent="financial_analyst", rationale="Strong fundamentals.",
            grade_short="A", grade_mid="S", grade_long="B",
            composite_score=72.5, composite_breakdown={"momentum": 20.0, "quality": 15.0},
        )
        s.add(sig)
        await s.flush()
        s.add(SignalOutcome(
            signal_id=sig.id, ticker="AAPL", signal_type="bullish",
            source_agent="financial_analyst", outcome_5d="correct",
        ))
        await s.commit()

    r = await client.get("/stocks/AAPL/analysis")
    assert r.status_code == 200
    body = r.json()
    assert body["has_analysis"] is True
    assert body["composite_score"] == 72.5
    assert body["composite_breakdown"] == {"momentum": 20.0, "quality": 15.0}
    assert body["grade_short"] == "A"
    assert body["accuracy_pct"] == 100.0
    assert len(body["outcomes"]) == 1


async def test_analysis_prefers_financial_analyst(client, db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as s:
        s.add(Signal(
            ticker="TSLA", signal_type="bearish", confidence=0.6,
            source_agent="sentiment_analyst",
        ))
        s.add(Signal(
            ticker="TSLA", signal_type="bullish", confidence=0.9,
            source_agent="financial_analyst", composite_score=55.0,
        ))
        await s.commit()

    r = await client.get("/stocks/TSLA/analysis")
    body = r.json()
    assert body["source_agent"] == "financial_analyst"
    assert body["composite_score"] == 55.0
