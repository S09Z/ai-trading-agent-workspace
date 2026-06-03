"""Tests for the news digest summariser.

Patches intelligence.summarizer.chat + _settings directly so tests are
independent of whether USE_LOCAL_LLM is set in .env.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from memory.database import Article

# Shared helpers ----------------------------------------------------------

def _mock_chat(text: str = "Digest OK"):
    """Return a patched chat() that yields a fake Claude response."""
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    return AsyncMock(return_value=response)


def _force_claude():
    """Context manager that forces the Claude path regardless of .env."""
    return patch("intelligence.summarizer._settings", use_local_llm=False)


# ── generate_digest ────────────────────────────────────────────────────────────

async def test_generate_digest_calls_claude():
    from intelligence.summarizer import generate_digest

    articles = [
        {"title": "NVDA beats earnings", "source": "reuters", "tickers": ["NVDA"]},
        {"title": "Fed holds rates steady", "source": "cnbc", "tickers": []},
    ]
    mock_chat = _mock_chat("Digest OK")
    with _force_claude(), patch("intelligence.summarizer.chat", new=mock_chat):
        result = await generate_digest(articles)

    assert result == "Digest OK"
    mock_chat.assert_called_once()


async def test_generate_digest_includes_titles_in_prompt():
    from intelligence.summarizer import generate_digest

    mock_chat = _mock_chat()
    with _force_claude(), patch("intelligence.summarizer.chat", new=mock_chat):
        await generate_digest([
            {"title": "AAPL iPhone sales surge", "source": "bloomberg", "tickers": ["AAPL"]}
        ])

    user_content = mock_chat.call_args.kwargs["messages"][0]["content"]
    assert "AAPL iPhone sales surge" in user_content


async def test_generate_digest_includes_tickers_in_prompt():
    from intelligence.summarizer import generate_digest

    mock_chat = _mock_chat()
    with _force_claude(), patch("intelligence.summarizer.chat", new=mock_chat):
        await generate_digest([
            {"title": "Tech rally", "source": "test", "tickers": ["NVDA", "MSFT"]}
        ])

    user_content = mock_chat.call_args.kwargs["messages"][0]["content"]
    assert "NVDA" in user_content
    assert "MSFT" in user_content


async def test_generate_digest_passes_system_prompt():
    """generate_digest must pass a non-empty system prompt to chat().
    cache_control wrapping is chat()'s responsibility (tested in test_claude_client.py).
    """
    from intelligence.summarizer import generate_digest

    mock_chat = _mock_chat()
    with _force_claude(), patch("intelligence.summarizer.chat", new=mock_chat):
        await generate_digest([{"title": "Test", "source": "x", "tickers": []}])

    system = mock_chat.call_args.kwargs.get("system", "")
    assert isinstance(system, str) and len(system) > 0


async def test_generate_digest_empty_returns_fallback():
    from intelligence.summarizer import generate_digest

    result = await generate_digest([])
    assert "No articles" in result


async def test_generate_digest_skips_empty_ticker_list():
    from intelligence.summarizer import generate_digest

    mock_chat = _mock_chat()
    with _force_claude(), patch("intelligence.summarizer.chat", new=mock_chat):
        await generate_digest([{"title": "Generic market update", "source": "ap", "tickers": []}])

    user_content = mock_chat.call_args.kwargs["messages"][0]["content"]
    assert "tickers:" not in user_content


# ── fetch_recent_articles ──────────────────────────────────────────────────────

async def test_fetch_recent_articles_returns_empty_when_db_empty(db_session):
    from intelligence.summarizer import fetch_recent_articles

    articles = await fetch_recent_articles(hours=6)
    assert articles == []


async def test_fetch_recent_articles_returns_recent_only(db_session, db_engine):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from intelligence.summarizer import fetch_recent_articles

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(Article(title="Recent news", source="test", url="https://example.com/r"))
        s.add(Article(
            title="Old news",
            source="test",
            url="https://example.com/o",
            collected_at=datetime.now(UTC) - timedelta(hours=48),
        ))
        await s.commit()

    articles = await fetch_recent_articles(hours=6)
    titles = [a["title"] for a in articles]
    assert "Recent news" in titles
    assert "Old news" not in titles


# ── build_digest ───────────────────────────────────────────────────────────────

async def test_build_digest_returns_tuple(db_session, mock_claude):
    from intelligence.summarizer import build_digest

    digest, count, signals, risk = await build_digest(hours=1)
    assert isinstance(digest, str)
    assert isinstance(count, int)
    assert isinstance(signals, list)
    assert isinstance(risk, dict)
    assert count == 0  # DB is empty


async def test_build_digest_no_articles_skips_claude(db_session):
    from intelligence.summarizer import build_digest

    with patch("intelligence.summarizer.chat", new=AsyncMock()) as mock_chat:
        digest, count, signals, risk = await build_digest(hours=1)

    assert count == 0
    assert "No articles" in digest
    mock_chat.assert_not_called()


async def test_generate_digest_includes_signals_in_prompt():
    from intelligence.summarizer import generate_digest

    signals = [{"ticker": "AAPL", "signal_type": "bullish", "confidence": 0.9}]
    mock_chat = _mock_chat()
    with _force_claude(), patch("intelligence.summarizer.chat", new=mock_chat):
        await generate_digest(
            [{"title": "AAPL beats", "source": "test", "tickers": ["AAPL"]}],
            signals=signals,
        )

    user_content = mock_chat.call_args.kwargs["messages"][0]["content"]
    assert "AAPL" in user_content
    assert "BULLISH" in user_content


async def test_generate_digest_includes_risk_in_prompt():
    from intelligence.summarizer import generate_digest

    risk = {"spike_count": 3, "circuit_open": True, "alert_count": 1}
    mock_chat = _mock_chat()
    with _force_claude(), patch("intelligence.summarizer.chat", new=mock_chat):
        await generate_digest(
            [{"title": "Market volatile", "source": "test", "tickers": []}],
            risk=risk,
        )

    user_content = mock_chat.call_args.kwargs["messages"][0]["content"]
    assert "spike" in user_content.lower()


async def test_generate_digest_no_signal_context_when_empty():
    from intelligence.summarizer import generate_digest

    mock_chat = _mock_chat()
    with _force_claude(), patch("intelligence.summarizer.chat", new=mock_chat):
        await generate_digest(
            [{"title": "Quiet day", "source": "test", "tickers": []}],
            signals=[],
            risk={"spike_count": 0, "circuit_open": False, "alert_count": 0},
        )

    user_content = mock_chat.call_args.kwargs["messages"][0]["content"]
    assert "Agent signals" not in user_content
    assert "Risk status" not in user_content
