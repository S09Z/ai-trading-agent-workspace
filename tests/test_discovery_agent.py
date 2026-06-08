"""Tests for DiscoveryAgent — real DB, mocked yfinance + LLM."""

from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from memory.database import AgentLog, Article, Signal

_MOCK_SNAP = {"price": 45.50, "volume": 5_000_000, "change_pct": 3.2}

_BULLISH_RESPONSE = (
    "SIGNAL: bullish\nCONFIDENCE: 0.78\n"
    "SHORT: A\nMID: A\nLONG: B\n"
    "RATIONALE: Multiple headlines indicate strong institutional interest and positive momentum."
)

_BEARISH_RESPONSE = (
    "SIGNAL: bearish\nCONFIDENCE: 0.70\n"
    "SHORT: C\nMID: C\nLONG: B\n"
    "RATIONALE: Declining volume and negative sentiment suggest near-term weakness."
)


def _make_article(title: str, content: str = "") -> MagicMock:
    art = MagicMock()
    art.title = title
    art.content = content
    return art


# ── _count_mentions ────────────────────────────────────────────────────────────

def test_count_mentions_finds_ticker():
    from agents.discovery_agent import _count_mentions

    articles = [_make_article("OKLO nuclear reactor deal announced")]
    counts = _count_mentions(articles)
    assert counts["OKLO"] == 1


def test_count_mentions_is_case_insensitive():
    from agents.discovery_agent import _count_mentions

    articles = [_make_article("oklo expands reactor fleet"), _make_article("OKLO secures funding")]
    counts = _count_mentions(articles)
    assert counts["OKLO"] == 2


def test_count_mentions_accumulates_across_articles():
    from agents.discovery_agent import _count_mentions

    articles = [
        _make_article("MRVL chip demand surges"),
        _make_article("MRVL beats earnings, OKLO also rises"),
    ]
    counts = _count_mentions(articles)
    assert counts["MRVL"] == 2
    assert counts["OKLO"] == 1


# ── _parse_response ────────────────────────────────────────────────────────────

def test_parse_response_bullish():
    from agents.discovery_agent import _parse_response

    sig, conf, gs, gm, gl, rationale = _parse_response(_BULLISH_RESPONSE)
    assert sig == "bullish"
    assert conf == 0.78
    assert gs == "A"
    assert gm == "A"
    assert gl == "B"
    assert "institutional" in rationale.lower()


def test_parse_response_bearish():
    from agents.discovery_agent import _parse_response

    sig, conf, gs, gm, gl, _ = _parse_response(_BEARISH_RESPONSE)
    assert sig == "bearish"
    assert conf == 0.70
    assert gs == "C"
    assert gm == "C"
    assert gl == "B"


def test_parse_response_defaults_on_missing_fields():
    from agents.discovery_agent import _parse_response

    sig, conf, gs, gm, gl, _ = _parse_response("Nothing structured here.")
    assert sig == "watchlist"
    assert conf == 0.5
    assert gs is None
    assert gm is None
    assert gl is None


# ── DiscoveryAgent.run ─────────────────────────────────────────────────────────

async def test_run_creates_signal_for_candidate(db_session, db_engine):
    from agents.discovery_agent import DiscoveryAgent

    # Seed 2 articles mentioning MRVL (in universe, not in mocked watchlist)
    for i in range(2):
        db_session.add(Article(
            title=f"MRVL chip demand report {i}",
            content="",
            source="test",
            url=f"https://example.com/mrvl-create-{i}",
        ))
    await db_session.commit()

    with patch("agents.discovery_agent._fetch_price", return_value=_MOCK_SNAP), \
         patch("agents.discovery_agent._settings") as s:
        s.watchlist = ["AAPL", "TSLA"]
        s.use_local_llm = False
        with patch(
            "intelligence.claude_client.analyze",
            new=AsyncMock(return_value=_BULLISH_RESPONSE),
        ):
            await DiscoveryAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        sig = (await s.execute(
            select(Signal).where(Signal.ticker == "MRVL", Signal.source_agent == "discovery_agent")
        )).scalars().first()

    assert sig is not None
    assert sig.signal_type == "bullish"
    assert sig.confidence == 0.78
    assert sig.grade_short == "A"
    assert sig.meta["mention_count"] == 2


async def test_run_skips_watchlist_tickers(db_session, db_engine):
    from agents.discovery_agent import DiscoveryAgent

    for i in range(3):
        db_session.add(Article(
            title=f"NVDA GPU sales record {i}",
            content="",
            source="test",
            url=f"https://example.com/nvda-{i}",
        ))
    await db_session.commit()

    mock_fetch = MagicMock(return_value=_MOCK_SNAP)
    with patch("agents.discovery_agent._fetch_price", mock_fetch), \
         patch("agents.discovery_agent._settings") as s:
        s.watchlist = ["NVDA", "AAPL", "TSLA"]  # NVDA is in watchlist
        await DiscoveryAgent().run()

    mock_fetch.assert_not_called()  # never reached price fetch for watchlist ticker

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        signals = (await s.execute(
            select(Signal).where(Signal.source_agent == "discovery_agent")
        )).scalars().all()

    assert signals == []


async def test_run_skips_below_min_mentions(db_session, db_engine):
    from agents.discovery_agent import DiscoveryAgent

    # Only 1 article mentions MRVL — below _MIN_MENTIONS=2
    db_session.add(Article(
        title="MRVL quarterly report",
        content="",
        source="test",
        url="https://example.com/mrvl-single",
    ))
    await db_session.commit()

    mock_fetch = MagicMock(return_value=_MOCK_SNAP)
    with patch("agents.discovery_agent._fetch_price", mock_fetch), \
         patch("agents.discovery_agent._settings") as s:
        s.watchlist = ["AAPL", "TSLA"]
        await DiscoveryAgent().run()

    mock_fetch.assert_not_called()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        signals = (await s.execute(
            select(Signal).where(Signal.source_agent == "discovery_agent")
        )).scalars().all()

    assert signals == []


async def test_run_skips_when_no_price_data(db_session, db_engine):
    from agents.discovery_agent import DiscoveryAgent

    for i in range(2):
        db_session.add(Article(
            title=f"MRVL Marvell earnings beat {i}",
            content="",
            source="test",
            url=f"https://example.com/mrvl-np-{i}",
        ))
    await db_session.commit()

    with patch("agents.discovery_agent._fetch_price", return_value=None), \
         patch("agents.discovery_agent._settings") as s:
        s.watchlist = ["AAPL"]
        await DiscoveryAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        signals = (await s.execute(
            select(Signal).where(Signal.source_agent == "discovery_agent")
        )).scalars().all()

    assert signals == []


async def test_run_skips_recently_discovered(db_session):
    from agents.discovery_agent import DiscoveryAgent

    # Pre-existing discovery signal for MRVL
    db_session.add(Signal(
        ticker="MRVL", signal_type="bullish", confidence=0.75,
        source_agent="discovery_agent",
    ))
    for i in range(2):
        db_session.add(Article(
            title=f"MRVL momentum continues {i}",
            content="",
            source="test",
            url=f"https://example.com/mrvl-skip-{i}",
        ))
    await db_session.commit()

    mock_fetch = MagicMock(return_value=_MOCK_SNAP)
    with patch("agents.discovery_agent._fetch_price", mock_fetch), \
         patch("agents.discovery_agent._settings") as s:
        s.watchlist = ["AAPL"]
        await DiscoveryAgent().run()

    mock_fetch.assert_not_called()  # skipped because recently discovered


async def test_run_no_articles_logs_and_returns(db_session):
    from agents.discovery_agent import DiscoveryAgent

    with patch("agents.discovery_agent._settings") as s:
        s.watchlist = ["AAPL"]
        await DiscoveryAgent().run()

    logs = (await db_session.execute(
        select(AgentLog).where(AgentLog.agent_name == "discovery_agent")
    )).scalars().all()

    assert any("No recent articles" in log.message for log in logs)


async def test_run_writes_agent_log(db_session, db_engine):
    from agents.discovery_agent import DiscoveryAgent

    for i in range(2):
        db_session.add(Article(
            title=f"MRVL partnerships grow {i}",
            content="",
            source="test",
            url=f"https://example.com/mrvl-log-{i}",
        ))
    await db_session.commit()

    with patch("agents.discovery_agent._fetch_price", return_value=_MOCK_SNAP), \
         patch("agents.discovery_agent._settings") as s:
        s.watchlist = ["AAPL"]
        s.use_local_llm = False
        with patch(
            "intelligence.claude_client.analyze",
            new=AsyncMock(return_value=_BULLISH_RESPONSE),
        ):
            await DiscoveryAgent().run()

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        logs = (await s.execute(
            select(AgentLog).where(AgentLog.agent_name == "discovery_agent")
        )).scalars().all()

    assert any(log.action == "discover" for log in logs)
    assert any(log.action == "run" for log in logs)
