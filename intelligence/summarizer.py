"""Fetch recent articles, signals, and risk status — generate a market digest.

Uses Claude by default. Set USE_LOCAL_LLM=true in .env to use Ollama instead.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from config.settings import get_settings
from memory.database import AgentLog, Article, AsyncSessionLocal, Signal

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


async def fetch_recent_signals(hours: int = 6, limit: int = 10) -> list[dict]:
    """Return the highest-confidence signals from Phase 3 agents in the last `hours` hours."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(Signal)
                .where(Signal.created_at >= since, Signal.ticker != "MARKET")
                .order_by(Signal.confidence.desc())
                .limit(limit)
            )
        ).scalars().all()
    return [
        {
            "ticker": s.ticker,
            "signal_type": s.signal_type,
            "confidence": s.confidence,
            "source_agent": s.source_agent,
            "rationale": s.rationale,
        }
        for s in rows
    ]


async def fetch_risk_status() -> dict:
    """Return the current risk snapshot: circuit breaker state, spike count, alert count."""
    cutoff_15m = datetime.now(UTC) - timedelta(minutes=15)
    cutoff_6h = datetime.now(UTC) - timedelta(hours=6)
    async with AsyncSessionLocal() as session:
        circuit_open = bool(
            (await session.execute(
                select(func.count()).select_from(AgentLog).where(
                    AgentLog.action == "circuit_breaker",
                    AgentLog.created_at >= cutoff_15m,
                )
            )).scalar()
        )
        spike_count = (await session.execute(
            select(func.count()).select_from(AgentLog).where(
                AgentLog.action == "spike_detected",
                AgentLog.created_at >= cutoff_15m,
            )
        )).scalar() or 0

        alert_count = (await session.execute(
            select(func.count()).select_from(Signal).where(
                Signal.signal_type == "alert",
                Signal.created_at >= cutoff_6h,
            )
        )).scalar() or 0

    return {
        "circuit_open": circuit_open,
        "spike_count": spike_count,
        "alert_count": alert_count,
    }


async def generate_digest(
    articles: list[dict],
    signals: list[dict] | None = None,
    risk: dict | None = None,
) -> str:
    """Summarise articles into a market digest, enriched with Phase 3 agent signals.

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

    if signals:
        signal_lines = "\n".join(
            f"- {s['ticker']} {s['signal_type'].upper()} confidence={s['confidence']:.2f}"
            for s in signals[:5]
        )
        prompt += f"\n\nAgent signals (use to reinforce Key Stories):\n{signal_lines}"

    if risk and (risk.get("spike_count", 0) > 0 or risk.get("circuit_open")):
        prompt += (
            f"\n\nRisk status: {risk['spike_count']} price spike(s) in last 15min"
            + (" — CIRCUIT OPEN" if risk.get("circuit_open") else "")
        )

    from intelligence.llm import analyze
    return await analyze(prompt, system=_SYSTEM, max_tokens=600)


async def build_digest(hours: int = 6) -> tuple[str, int, list[dict], dict]:
    """Fetch articles, signals, and risk status — generate a full digest.

    Returns (digest_text, article_count, signals, risk).
    """
    articles = await fetch_recent_articles(hours=hours)
    signals = await fetch_recent_signals(hours=hours)
    risk = await fetch_risk_status()
    digest = await generate_digest(articles, signals=signals, risk=risk)
    return digest, len(articles), signals, risk
