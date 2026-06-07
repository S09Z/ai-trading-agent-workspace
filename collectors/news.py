import asyncio
import re
from datetime import UTC, datetime
from time import mktime

import feedparser

from config.settings import get_settings

_settings = get_settings()

RSS_FEEDS: dict[str, str] = {
    "reuters": "https://feeds.reuters.com/reuters/businessNews",
    "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "marketwatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "yahoo_finance": "https://finance.yahoo.com/rss/topstories",
    "investing": "https://www.investing.com/rss/news.rss",
    # Macro / policy feeds
    "federal_reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
    "eia_oil": "https://www.eia.gov/rss/press_releases.xml",
    "reuters_macro": "https://feeds.reuters.com/reuters/economicNews",
}

# Targeted feeds for small-cap tickers not well-covered by mainstream RSS.
# Articles from these feeds are force-tagged with the mapped ticker.
TARGETED_FEEDS: dict[str, list[str]] = {
    "OKLO": [
        "https://news.google.com/rss/search?q=Oklo+nuclear+reactor&hl=en-US&gl=US&ceid=US:en",
        "https://www.world-nuclear-news.org/rss",
    ],
    "SMR": [
        "https://news.google.com/rss/search?q=NuScale+Power+small+modular+reactor&hl=en-US&gl=US&ceid=US:en",
    ],
    "TMDX": [
        "https://news.google.com/rss/search?q=TransMedics+organ+transplant&hl=en-US&gl=US&ceid=US:en",
        "https://medcitynews.com/feed/",
    ],
}


# Company name / topic aliases so "Amazon" matches AMZN, "crude oil" matches USO, etc.
_ALIASES: dict[str, list[str]] = {
    "AAPL": ["Apple"],
    "TSLA": ["Tesla"],
    "NVDA": ["Nvidia", "NVIDIA"],
    "MSFT": ["Microsoft"],
    "AMZN": ["Amazon"],
    "META": ["Meta", "Facebook"],
    "GOOGL": ["Google", "Alphabet"],
    "NFLX": ["Netflix"],
    # Macro instruments
    "USO":  ["crude oil", "WTI", "Brent", "oil price", "petroleum", "OPEC", "oil supply",
             "oil shortage", "oil demand", "barrel"],
    "GLD":  ["gold", "gold price", "gold futures", "safe haven"],
    "TLT":  ["treasury", "bond yield", "10-year yield", "10yr yield", "T-bill",
             "interest rate", "rate hike", "rate cut", "Federal Reserve", "Fed decision",
             "FOMC", "Powell"],
    "DXY":  ["dollar index", "US dollar", "dollar strength", "dollar weakness", "forex"],
}


def _extract_tickers(text: str) -> list[str]:
    """Return watchlist tickers mentioned in text (ticker symbol or company name match)."""
    found = []
    for ticker in _settings.watchlist:
        terms = [ticker] + _ALIASES.get(ticker, [])
        if any(re.search(rf"\b{re.escape(t)}\b", text, re.IGNORECASE) for t in terms):
            found.append(ticker)
    return found


def _parse_feed(feed_name: str, url: str) -> list[dict]:
    """Parse a single RSS feed and return normalised article dicts."""
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        if not title or not link:
            continue

        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].value
        else:
            content = getattr(entry, "summary", "")

        published_at: datetime | None = None
        raw_date = getattr(entry, "published_parsed", None)
        if raw_date:
            published_at = datetime.fromtimestamp(mktime(raw_date), tz=UTC)

        articles.append({
            "title": title,
            "content": content,
            "source": feed_name,
            "url": link,
            "published_at": published_at,
            "tickers": _extract_tickers(title + " " + content),
        })
    return articles


async def fetch_rss_feed(feed_name: str, url: str) -> list[dict]:
    """Async wrapper — runs feedparser in a thread so it doesn't block the loop."""
    return await asyncio.to_thread(_parse_feed, feed_name, url)


def _parse_targeted_feed(ticker: str, url: str) -> list[dict]:
    """Parse a targeted feed and force-tag every article with the given ticker.

    Used for small-cap stocks not reliably detected by alias matching.
    Still runs normal extraction so co-mentioned tickers are also captured.
    """
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        if not title or not link:
            continue

        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].value
        else:
            content = getattr(entry, "summary", "")

        published_at: datetime | None = None
        raw_date = getattr(entry, "published_parsed", None)
        if raw_date:
            published_at = datetime.fromtimestamp(mktime(raw_date), tz=UTC)

        tickers = _extract_tickers(title + " " + content)
        if ticker not in tickers:
            tickers = [ticker] + tickers  # guarantee force-tag is first

        articles.append({
            "title": title,
            "content": content,
            "source": f"targeted:{ticker.lower()}",
            "url": link,
            "published_at": published_at,
            "tickers": tickers,
        })
    return articles


async def fetch_targeted_feeds() -> list[dict]:
    """Fetch all targeted small-cap feeds concurrently."""
    tasks = [
        asyncio.to_thread(_parse_targeted_feed, ticker, url)
        for ticker, urls in TARGETED_FEEDS.items()
        for url in urls
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    articles: list[dict] = []
    for batch in results:
        if not isinstance(batch, Exception):
            articles.extend(batch)
    return articles


async def fetch_newsapi() -> list[dict]:
    """Fetch from NewsAPI. Returns [] if no API key is configured."""
    if not _settings.news_api_key:
        return []

    def _fetch() -> list[dict]:
        from newsapi import NewsApiClient

        client = NewsApiClient(api_key=_settings.news_api_key)
        response = client.get_everything(
            q="stock market OR earnings OR Federal Reserve",
            language="en",
            sort_by="publishedAt",
            page_size=100,
        )
        articles = []
        for a in response.get("articles", []):
            if not a.get("title") or not a.get("url"):
                continue
            body = a.get("content") or a.get("description") or ""
            published_at: datetime | None = None
            if a.get("publishedAt"):
                published_at = datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
            articles.append({
                "title": a["title"],
                "content": body,
                "source": (a.get("source") or {}).get("name", "newsapi"),
                "url": a["url"],
                "published_at": published_at,
                "tickers": _extract_tickers(a["title"] + " " + body),
            })
        return articles

    return await asyncio.to_thread(_fetch)


async def fetch_all() -> list[dict]:
    """Fetch all RSS feeds + NewsAPI + targeted small-cap feeds, deduplicate by URL."""
    tasks = [fetch_rss_feed(name, url) for name, url in RSS_FEEDS.items()]
    tasks.append(fetch_newsapi())
    tasks.append(fetch_targeted_feeds())

    results = await asyncio.gather(*tasks, return_exceptions=True)

    seen: set[str] = set()
    articles: list[dict] = []
    for batch in results:
        if isinstance(batch, Exception):
            continue
        for article in batch:
            url = article.get("url", "")
            if url and url not in seen:
                seen.add(url)
                articles.append(article)
    return articles
