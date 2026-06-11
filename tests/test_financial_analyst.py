"""Tests for FinancialAnalystAgent — real DB, mocked yfinance + LLM."""

from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from memory.database import AgentLog, Signal

_STRONG_METRICS = {
    "revenueGrowth": 0.20,
    "earningsGrowth": 0.30,
    "profitMargins": 0.25,
    "grossMargins": 0.45,
    "operatingMargins": 0.30,
    "returnOnEquity": 1.2,
    "debtToEquity": 50.0,
    "currentRatio": 1.5,
    "freeCashflow": 90_000_000_000,
    "trailingPE": 28.0,
    "forwardPE": 24.0,
    "priceToSalesTrailing12Months": 8.5,
    "totalCash": 60_000_000_000,
    "totalDebt": 80_000_000_000,
    "marketCap": 3_000_000_000_000,
    "trailingEps": 6.5,
    "forwardEps": 8.0,
}

_WEAK_METRICS = {
    "revenueGrowth": -0.10,
    "earningsGrowth": -0.25,
    "profitMargins": -0.05,
    "grossMargins": 0.15,
    "operatingMargins": -0.02,
    "debtToEquity": 300.0,
    "currentRatio": 0.6,
    "freeCashflow": -5_000_000_000,
    "trailingPE": 80.0,
    "totalCash": 1_000_000_000,
    "totalDebt": 50_000_000_000,
}

_BULLISH_RESPONSE = (
    "SIGNAL: bullish\nCONFIDENCE: 0.85\n"
    "SHORT: A\nMID: S\nLONG: A\n"
    "RATIONALE: Strong revenue growth and healthy margins indicate robust fundamentals."
)

_BEARISH_RESPONSE = (
    "SIGNAL: bearish\nCONFIDENCE: 0.80\n"
    "SHORT: C\nMID: C\nLONG: B\n"
    "RATIONALE: Declining revenue and negative margins signal financial distress."
)


def test_parse_response_bullish():
    from agents.financial_analyst import _parse_response
    sig, conf, gs, gm, gl, rationale = _parse_response(_BULLISH_RESPONSE)
    assert sig == "bullish"
    assert conf == 0.85
    assert gs == "A"
    assert gm == "S"
    assert gl == "A"
    assert "revenue" in rationale.lower()


def test_parse_response_bearish():
    from agents.financial_analyst import _parse_response
    sig, conf, gs, gm, gl, _ = _parse_response(_BEARISH_RESPONSE)
    assert sig == "bearish"
    assert conf == 0.80
    assert gs == "C"
    assert gm == "C"
    assert gl == "B"


def test_parse_response_defaults_on_missing_fields():
    from agents.financial_analyst import _parse_response
    sig, conf, gs, gm, gl, _ = _parse_response("No structured data here.")
    assert sig == "watchlist"
    assert conf == 0.5
    assert gs is None
    assert gm is None
    assert gl is None


def test_fmt_metrics_formats_correctly():
    from agents.financial_analyst import _fmt_metrics
    out = _fmt_metrics({"revenueGrowth": 0.20, "freeCashflow": 90_000_000_000, "trailingPE": 28.0})
    assert "20.0%" in out
    assert "$90.00B" in out
    assert "28.00" in out


async def test_run_creates_bullish_signal(db_session, db_engine):
    from agents.financial_analyst import FinancialAnalystAgent

    with patch("agents.financial_analyst._fetch_metrics", return_value=_STRONG_METRICS), \
         patch("agents.financial_analyst._settings") as s, \
         patch("agents.financial_analyst.get_factor_context", new=AsyncMock(return_value="")), \
         patch("intelligence.llm.analyze", new=AsyncMock(return_value=_BULLISH_RESPONSE)):
        s.watchlist = ["AAPL"]
        await FinancialAnalystAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        sig = (await s.execute(
            select(Signal).where(Signal.ticker == "AAPL", Signal.source_agent == "financial_analyst")
        )).scalars().first()

    assert sig is not None
    assert sig.signal_type == "bullish"
    assert sig.confidence == 0.85
    assert sig.grade_short == "A"
    assert sig.grade_mid == "S"
    assert sig.grade_long == "A"


async def test_run_creates_bearish_signal(db_session, db_engine):
    from agents.financial_analyst import FinancialAnalystAgent

    with patch("agents.financial_analyst._fetch_metrics", return_value=_WEAK_METRICS), \
         patch("agents.financial_analyst._settings") as s, \
         patch("agents.financial_analyst.get_factor_context", new=AsyncMock(return_value="")), \
         patch("intelligence.llm.analyze", new=AsyncMock(return_value=_BEARISH_RESPONSE)):
        s.watchlist = ["TSLA"]
        await FinancialAnalystAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        sig = (await s.execute(
            select(Signal).where(Signal.ticker == "TSLA", Signal.source_agent == "financial_analyst")
        )).scalars().first()

    assert sig.signal_type == "bearish"
    assert sig.grade_short == "C"


async def test_skips_when_insufficient_metrics(db_session, db_engine):
    from agents.financial_analyst import FinancialAnalystAgent

    with patch("agents.financial_analyst._fetch_metrics", return_value={"trailingPE": 30.0}), \
         patch("agents.financial_analyst._settings") as s:
        s.watchlist = ["NVDA"]
        await FinancialAnalystAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        signals = (await s.execute(
            select(Signal).where(Signal.source_agent == "financial_analyst")
        )).scalars().all()

    assert signals == []


async def test_skips_recently_analyzed_ticker(db_session, db_engine):
    from agents.financial_analyst import FinancialAnalystAgent

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(Signal(
            ticker="MSFT", signal_type="bullish", confidence=0.8,
            source_agent="financial_analyst",
        ))
        await s.commit()

    mock_fetch = MagicMock(return_value=_STRONG_METRICS)
    with patch("agents.financial_analyst._fetch_metrics", mock_fetch), \
         patch("agents.financial_analyst._settings") as s:
        s.watchlist = ["MSFT"]
        await FinancialAnalystAgent().run()

    mock_fetch.assert_not_called()


async def test_run_specific_ticker(db_session, db_engine):
    from agents.financial_analyst import FinancialAnalystAgent

    with patch("agents.financial_analyst._fetch_metrics", return_value=_STRONG_METRICS), \
         patch("agents.financial_analyst._settings") as s, \
         patch("agents.financial_analyst.get_factor_context", new=AsyncMock(return_value="")), \
         patch("intelligence.llm.analyze", new=AsyncMock(return_value=_BULLISH_RESPONSE)):
        s.watchlist = ["AAPL", "TSLA", "NVDA"]
        await FinancialAnalystAgent().run(ticker="NVDA")

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        signals = (await s.execute(
            select(Signal).where(Signal.source_agent == "financial_analyst")
        )).scalars().all()

    assert len(signals) == 1
    assert signals[0].ticker == "NVDA"


async def test_run_writes_agent_log(db_session, db_engine):
    from agents.financial_analyst import FinancialAnalystAgent

    with patch("agents.financial_analyst._fetch_metrics", return_value=_STRONG_METRICS), \
         patch("agents.financial_analyst._settings") as s, \
         patch("agents.financial_analyst.get_factor_context", new=AsyncMock(return_value="")), \
         patch("intelligence.llm.analyze", new=AsyncMock(return_value=_BULLISH_RESPONSE)):
        s.watchlist = ["AAPL"]
        await FinancialAnalystAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        logs = (await s.execute(
            select(AgentLog).where(AgentLog.agent_name == "financial_analyst")
        )).scalars().all()

    assert any(log.action == "analyze" for log in logs)
    assert any(log.action == "run" for log in logs)
