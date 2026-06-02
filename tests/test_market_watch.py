"""Tests for MarketWatchAgent.

Uses real PostgreSQL (db_session for cleanup) and mocks fetch_watchlist_snapshots.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from memory.database import AgentLog, MarketSnapshot


def _snap(ticker: str = "AAPL", change_pct: float = 0.5) -> dict:
    return {
        "ticker": ticker,
        "timestamp": datetime.now(UTC).replace(second=0, microsecond=0),
        "open": 180.0,
        "high": 185.0,
        "low": 179.0,
        "close": 182.0,
        "volume": 50_000_000.0,
        "change_pct": change_pct,
    }


# ── tests ──────────────────────────────────────────────────────────────────────

async def test_run_stores_snapshots(db_session, db_engine):
    from agents.market_watch import MarketWatchAgent

    snaps = [_snap("AAPL"), _snap("TSLA")]
    with patch("agents.market_watch.fetch_watchlist_snapshots", new=AsyncMock(return_value=snaps)):
        await MarketWatchAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        rows = (await s.execute(select(MarketSnapshot))).scalars().all()

    tickers = {r.ticker for r in rows}
    assert "AAPL" in tickers
    assert "TSLA" in tickers


async def test_run_detects_spike_above_threshold(db_session, db_engine):
    from agents.market_watch import MarketWatchAgent

    snaps = [_snap("NVDA", change_pct=5.2)]
    with patch("agents.market_watch.fetch_watchlist_snapshots", new=AsyncMock(return_value=snaps)):
        await MarketWatchAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        spike_logs = (
            await s.execute(
                select(AgentLog).where(
                    AgentLog.agent_name == "market_watch",
                    AgentLog.action == "spike_detected",
                )
            )
        ).scalars().all()

    assert len(spike_logs) == 1
    assert "NVDA" in spike_logs[0].message
    assert spike_logs[0].level == "warning"


async def test_run_no_spike_below_threshold(db_session, db_engine):
    from agents.market_watch import MarketWatchAgent

    snaps = [_snap("AAPL", change_pct=1.0)]
    with patch("agents.market_watch.fetch_watchlist_snapshots", new=AsyncMock(return_value=snaps)):
        await MarketWatchAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        spike_logs = (
            await s.execute(
                select(AgentLog).where(
                    AgentLog.agent_name == "market_watch",
                    AgentLog.action == "spike_detected",
                )
            )
        ).scalars().all()

    assert spike_logs == []


async def test_run_detects_negative_spike(db_session, db_engine):
    from agents.market_watch import MarketWatchAgent

    snaps = [_snap("SPY", change_pct=-4.1)]
    with patch("agents.market_watch.fetch_watchlist_snapshots", new=AsyncMock(return_value=snaps)):
        await MarketWatchAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        spike_logs = (
            await s.execute(
                select(AgentLog).where(AgentLog.action == "spike_detected")
            )
        ).scalars().all()

    assert len(spike_logs) == 1
    assert "SPY" in spike_logs[0].message


async def test_run_writes_poll_log(db_session, db_engine):
    from agents.market_watch import MarketWatchAgent

    with patch("agents.market_watch.fetch_watchlist_snapshots", new=AsyncMock(return_value=[])):
        await MarketWatchAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        logs = (
            await s.execute(
                select(AgentLog).where(
                    AgentLog.agent_name == "market_watch",
                    AgentLog.action == "poll",
                )
            )
        ).scalars().all()

    assert len(logs) == 1


async def test_run_skips_duplicate_snapshot(db_session, db_engine):
    """Same (ticker, timestamp) → second insert is silently dropped."""
    from agents.market_watch import MarketWatchAgent

    snaps = [_snap("AAPL")]
    with patch("agents.market_watch.fetch_watchlist_snapshots", new=AsyncMock(return_value=snaps)):
        await MarketWatchAgent().run()
    with patch("agents.market_watch.fetch_watchlist_snapshots", new=AsyncMock(return_value=snaps)):
        await MarketWatchAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        rows = (
            await s.execute(select(MarketSnapshot).where(MarketSnapshot.ticker == "AAPL"))
        ).scalars().all()

    assert len(rows) == 1
