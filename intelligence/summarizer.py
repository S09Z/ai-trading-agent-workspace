"""Fetch recent articles from the DB and generate a market digest.

Uses Claude by default. Set USE_LOCAL_LLM=true in .env to use Ollama instead.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from config.settings import get_settings
from intelligence.claude_client import chat
from memory.database import Article, AsyncSessionLocal

_settings = get_settings()

_SYSTEM = """\
You are a professional financial analyst writing a concise market news digest.

Analyse the articles provided and return EXACTLY this structure (no extra text):

**🔑 Key Stories**
• [TICKER or MACRO]: One-sentence summary. [BULLISH / BEARISH / NEUTRAL]
(up to 5 stories — most market-moving first)

**📈 Notable Tickers**
List each ticker with a directional tag: AAPL ▲ TSLA ▼ SPY ➡
(omit if no clear movers)

**🌐 Macro Theme**
One sentence on the dominant market narrative.

Keep the full digest under 280 words. Be direct and factual. No waffle.\
"""


async def fetch_recent_articles(hours: int = 6, limit: int = 30) -> list[dict]:
    """Return articles collected in the last `hours` hours."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(Article)
                .where(Article.collected_at >= since)
                .order_by(Article.collected_at.desc())
                .limit(limit)
            )
        ).scalars().all()
    return [{"title": a.title, "source": a.source, "tickers": a.tickers} for a in rows]


async def generate_digest(articles: list[dict]) -> str:
    """Summarise a list of article dicts into a market digest.

    Routes to Ollama (local) when USE_LOCAL_LLM=true, otherwise uses Claude.
    """
    if not articles:
        return "No articles collected in this period."

    article_list = "\n".join(
        f"- [{a['source']}] {a['title']}"
        + (f" (tickers: {', '.join(a['tickers'])})" if a.get("tickers") else "")
        for a in articles
    )
    prompt = f"Articles:\n\n{article_list}"

    if _settings.use_local_llm:
        from intelligence.local_client import chat_local
        return await chat_local(prompt, system=_SYSTEM, max_tokens=600)

    response = await chat(
        messages=[{"role": "user", "content": prompt}],
        system=_SYSTEM,
        max_tokens=600,
    )
    return response.content[0].text


async def build_digest(hours: int = 6) -> tuple[str, int]:
    """Fetch recent articles and generate a digest.

    Returns (digest_text, article_count).
    """
    articles = await fetch_recent_articles(hours=hours)
    return await generate_digest(articles), len(articles)
