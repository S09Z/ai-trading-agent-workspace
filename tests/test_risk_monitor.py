"""Tests for RiskMonitorAgent — real DB, no external mocks needed."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from memory.database import AgentLog, Signal


async def _insert_spike_logs(db_engine, count: int) -> None:
    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        for i in range(count):
            s.add(AgentLog(
                agent_name="market_watch",
                action="spike_detected",
                message=f"AAPL +4.0% spike {i}",
                level="warning",
            ))
        await s.commit()


# ── normal scan ────────────────────────────────────────────────────────────────

async def test_run_logs_scan_on_no_spikes(db_session, db_engine):
    from agents.risk_monitor import RiskMonitorAgent

    await RiskMonitorAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        logs = (await s.execute(
            select(AgentLog).where(
                AgentLog.agent_name == "risk_monitor",
                AgentLog.action == "scan",
            )
        )).scalars().all()

    assert len(logs) == 1
    assert "0/" in logs[0].message


async def test_run_creates_alert_signal_on_minor_spikes(db_session, db_engine):
    from agents.risk_monitor import RiskMonitorAgent

    await _insert_spike_logs(db_engine, 1)
    await RiskMonitorAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        signals = (await s.execute(
            select(Signal).where(Signal.signal_type == "alert")
        )).scalars().all()

    assert len(signals) == 1
    assert signals[0].ticker == "MARKET"
    assert signals[0].source_agent == "risk_monitor"


# ── circuit breaker ────────────────────────────────────────────────────────────

async def test_run_opens_circuit_on_threshold_spikes(db_session, db_engine):
    from agents.risk_monitor import CIRCUIT_THRESHOLD, RiskMonitorAgent

    await _insert_spike_logs(db_engine, CIRCUIT_THRESHOLD)
    await RiskMonitorAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        cb_logs = (await s.execute(
            select(AgentLog).where(AgentLog.action == "circuit_breaker")
        )).scalars().all()

    assert len(cb_logs) == 1
    assert cb_logs[0].level == "warning"
    assert "Circuit OPEN" in cb_logs[0].message


async def test_circuit_breaker_skips_signal_creation(db_session, db_engine):
    from agents.risk_monitor import CIRCUIT_THRESHOLD, RiskMonitorAgent

    await _insert_spike_logs(db_engine, CIRCUIT_THRESHOLD)
    await RiskMonitorAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        signals = (await s.execute(select(Signal))).scalars().all()

    assert signals == []


# ── is_halted ──────────────────────────────────────────────────────────────────

async def test_is_halted_false_by_default(db_session):
    from agents.risk_monitor import RiskMonitorAgent

    assert await RiskMonitorAgent().is_halted() is False


async def test_is_halted_true_after_circuit_breaker(db_session, db_engine):
    from agents.risk_monitor import RiskMonitorAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(AgentLog(
            agent_name="risk_monitor",
            action="circuit_breaker",
            message="Circuit OPEN",
            level="warning",
        ))
        await s.commit()

    assert await RiskMonitorAgent().is_halted() is True


async def test_is_halted_false_for_old_circuit_breaker(db_session, db_engine):
    from agents.risk_monitor import RiskMonitorAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        old_log = AgentLog(
            agent_name="risk_monitor",
            action="circuit_breaker",
            message="Circuit OPEN",
            level="warning",
        )
        s.add(old_log)
        await s.commit()
        await s.refresh(old_log)
        old_log.created_at = datetime.now(UTC) - timedelta(hours=1)
        await s.commit()

    assert await RiskMonitorAgent().is_halted() is False
