"""Tests for the news collector — RSS and NewsAPI fetch + normalisation.

All network calls are mocked — no real HTTP requests.
"""

from datetime import datetime
from time import struct_time
from unittest.mock import AsyncMock, MagicMock, patch

# ── helpers ────────────────────────────────────────────────────────────────────

def _make_entry(
    title="NVDA beats earnings expectations",
    link="https://reuters.com/nvda-earnings",
    summary="NVIDIA reported record revenue...",
    content=None,
    published_parsed=None,
):
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.summary = summary
    entry.content = [MagicMock(value=content)] if content else []
    entry.published_parsed = published_parsed or struct_time((2024, 1, 15, 14, 30, 0, 0, 15, 0))
    # feedparser entries may not have a 'content' attr at all
    if not content:
        del entry.content
    return entry


def _make_feed(*entries):
    feed = MagicMock()
    feed.entries = list(entries)
    return feed


# ── _parse_feed ────────────────────────────────────────────────────────────────

def test_parse_feed_normalises_entry():
    from collectors.news import _parse_feed

    with patch("collectors.news.feedparser.parse", return_value=_make_feed(_make_entry())):
        results = _parse_feed("reuters", "https://feeds.reuters.com/test")

    assert len(results) == 1
    a = results[0]
    assert a["title"] == "NVDA beats earnings expectations"
    assert a["url"] == "https://reuters.com/nvda-earnings"
    assert a["source"] == "reuters"
    assert isinstance(a["published_at"], datetime)
    assert a["published_at"].tzinfo is not None


def test_parse_feed_uses_content_over_summary():
    from collectors.news import _parse_feed

    entry = _make_entry(content="Full article body")
    with patch("collectors.news.feedparser.parse", return_value=_make_feed(entry)):
        results = _parse_feed("cnbc", "https://cnbc.com/rss")

    assert results[0]["content"] == "Full article body"


def test_parse_feed_falls_back_to_summary():
    from collectors.news import _parse_feed

    with patch("collectors.news.feedparser.parse", return_value=_make_feed(_make_entry())):
        results = _parse_feed("cnbc", "https://cnbc.com/rss")

    assert "NVIDIA" in results[0]["content"]


def test_parse_feed_skips_entry_without_title():
    from collectors.news import _parse_feed

    entry = _make_entry(title="", link="https://example.com/a")
    with patch("collectors.news.feedparser.parse", return_value=_make_feed(entry)):
        results = _parse_feed("test", "https://example.com/feed")

    assert results == []


def test_parse_feed_skips_entry_without_url():
    from collectors.news import _parse_feed

    entry = _make_entry(link="")
    with patch("collectors.news.feedparser.parse", return_value=_make_feed(entry)):
        results = _parse_feed("test", "https://example.com/feed")

    assert results == []


def test_parse_feed_handles_missing_published_date():
    from collectors.news import _parse_feed

    entry = _make_entry()
    del entry.published_parsed
    with patch("collectors.news.feedparser.parse", return_value=_make_feed(entry)):
        results = _parse_feed("test", "https://example.com/feed")

    assert results[0]["published_at"] is None


# ── _extract_tickers ───────────────────────────────────────────────────────────

def test_extract_tickers_finds_watchlist_match():
    from collectors.news import _extract_tickers

    tickers = _extract_tickers("NVDA stock surges after record GPU sales")
    assert "NVDA" in tickers


def test_extract_tickers_finds_multiple():
    from collectors.news import _extract_tickers

    tickers = _extract_tickers("AAPL and MSFT both rallied on the news")
    assert "AAPL" in tickers
    assert "MSFT" in tickers


def test_extract_tickers_returns_empty_for_no_match():
    from collectors.news import _extract_tickers

    tickers = _extract_tickers("Weather forecast for the northeast this weekend")
    assert tickers == []


def test_extract_tickers_is_case_insensitive():
    from collectors.news import _extract_tickers

    tickers = _extract_tickers("nvda reports record earnings")
    assert "NVDA" in tickers


# ── fetch_all ──────────────────────────────────────────────────────────────────

async def test_fetch_all_deduplicates_by_url():
    from collectors.news import fetch_all

    article = {
        "title": "Test",
        "url": "https://example.com/same",
        "source": "a",
        "content": "",
        "published_at": None,
        "tickers": [],
    }
    # Two sources return the same URL
    with patch("collectors.news.fetch_rss_feed", new=AsyncMock(return_value=[article])), \
         patch("collectors.news.fetch_newsapi", new=AsyncMock(return_value=[article])):
        results = await fetch_all()

    urls = [r["url"] for r in results]
    assert urls.count("https://example.com/same") == 1


async def test_fetch_all_skips_failed_source():
    from collectors.news import fetch_all

    good = [{"title": "OK", "url": "https://example.com/ok", "source": "b",
             "content": "", "published_at": None, "tickers": []}]

    async def boom(*_):
        raise RuntimeError("feed down")

    with patch("collectors.news.fetch_rss_feed", new=AsyncMock(side_effect=boom)), \
         patch("collectors.news.fetch_newsapi", new=AsyncMock(return_value=good)):
        results = await fetch_all()

    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/ok"


async def test_fetch_newsapi_returns_empty_without_key():
    from collectors.news import fetch_newsapi

    with patch("collectors.news._settings") as mock_settings:
        mock_settings.news_api_key = ""
        results = await fetch_newsapi()

    assert results == []
