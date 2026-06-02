"""Tests for the news digest summariser.

Claude calls are mocked — no real API usage.
"""

from unittest.mock import AsyncMock, patch

from memory.database import Article

# ── generate_digest ────────────────────────────────────────────────────────────

async def test_generate_digest_calls_claude(mock_claude):
    from intelligence.summarizer import generate_digest

    articles = [
        {"title": "NVDA beats earnings", "source": "reuters", "tickers": ["NVDA"]},
        {"title": "Fed holds rates steady", "source": "cnbc", "tickers": []},
    ]
    result = await generate_digest(articles)

    assert result == "OK"
    mock_claude.messages.create.assert_called_once()


async def test_generate_digest_includes_titles_in_prompt(mock_claude):
    from intelligence.summarizer import generate_digest

    articles = [{"title": "AAPL iPhone sales surge", "source": "bloomberg", "tickers": ["AAPL"]}]
    await generate_digest(articles)

    call_kwargs = mock_claude.messages.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "AAPL iPhone sales surge" in user_content


async def test_generate_digest_includes_tickers_in_prompt(mock_claude):
    from intelligence.summarizer import generate_digest

    articles = [{"title": "Tech rally", "source": "test", "tickers": ["NVDA", "MSFT"]}]
    await generate_digest(articles)

    call_kwargs = mock_claude.messages.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "NVDA" in user_content
    assert "MSFT" in user_content


async def test_generate_digest_uses_cached_system_prompt(mock_claude):
    """System prompt must have cache_control — reduces token cost on repeated calls."""
    from intelligence.summarizer import generate_digest

    await generate_digest([{"title": "Test", "source": "x", "tickers": []}])

    call_kwargs = mock_claude.messages.create.call_args.kwargs
    system = call_kwargs.get("system", [])
    assert len(system) == 1
    assert system[0]["cache_control"] == {"type": "ephemeral"}


async def test_generate_digest_empty_returns_fallback():
    from intelligence.summarizer import generate_digest

    result = await generate_digest([])
    assert "No articles" in result
    # No Claude call should be made for empty input


async def test_generate_digest_skips_empty_ticker_list(mock_claude):
    from intelligence.summarizer import generate_digest

    articles = [{"title": "Generic market update", "source": "ap", "tickers": []}]
    await generate_digest(articles)

    call_kwargs = mock_claude.messages.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    # No ticker annotation when tickers list is empty
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

    digest, count = await build_digest(hours=1)
    assert isinstance(digest, str)
    assert isinstance(count, int)
    assert count == 0  # DB is empty


async def test_build_digest_no_articles_skips_claude(db_session):
    from intelligence.summarizer import build_digest

    with patch("intelligence.summarizer.chat", new=AsyncMock()) as mock_chat:
        digest, count = await build_digest(hours=1)

    assert count == 0
    assert "No articles" in digest
    mock_chat.assert_not_called()
