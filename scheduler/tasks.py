import asyncio

from celery import Celery
from celery.schedules import crontab

from config.settings import get_settings

_settings = get_settings()

celery_app = Celery("alphaops")
celery_app.conf.update(
    broker_url=_settings.celery_broker_url,
    result_backend=_settings.celery_result_backend,
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
)


# ── Phase 2 tasks ──────────────────────────────────────────────────────────────

@celery_app.task(name="scheduler.tasks.run_news_hunter")
def run_news_hunter() -> None:
    from agents.news_hunter import NewsHunterAgent
    asyncio.run(NewsHunterAgent().run())


@celery_app.task(name="scheduler.tasks.run_market_watch")
def run_market_watch() -> None:
    from agents.market_watch import MarketWatchAgent
    asyncio.run(MarketWatchAgent().run())


# ── Phase 3 tasks ──────────────────────────────────────────────────────────────

@celery_app.task(name="scheduler.tasks.run_sentiment_analyst")
def run_sentiment_analyst() -> None:
    from agents.sentiment_analyst import SentimentAnalystAgent
    asyncio.run(SentimentAnalystAgent().run())


@celery_app.task(name="scheduler.tasks.run_risk_monitor")
def run_risk_monitor() -> None:
    from agents.risk_monitor import RiskMonitorAgent
    asyncio.run(RiskMonitorAgent().run())


@celery_app.task(name="scheduler.tasks.run_research_analyst")
def run_research_analyst(ticker: str | None = None) -> None:
    from agents.research_analyst import ResearchAnalystAgent
    asyncio.run(ResearchAnalystAgent().run(ticker=ticker))


@celery_app.task(name="scheduler.tasks.run_orchestrator")
def run_orchestrator() -> None:
    from agents.orchestrator import OrchestratorAgent
    asyncio.run(OrchestratorAgent().run())


# ── Financial analysis tasks ───────────────────────────────────────────────────

@celery_app.task(name="scheduler.tasks.run_financial_analyst")
def run_financial_analyst(ticker: str | None = None) -> None:
    from agents.financial_analyst import FinancialAnalystAgent
    asyncio.run(FinancialAnalystAgent().run(ticker=ticker))


# ── Discovery tasks ────────────────────────────────────────────────────────────

@celery_app.task(name="scheduler.tasks.run_discovery_agent")
def run_discovery_agent() -> None:
    from agents.discovery_agent import DiscoveryAgent
    asyncio.run(DiscoveryAgent().run())


# ── Phase 8 tasks ──────────────────────────────────────────────────────────────

@celery_app.task(name="scheduler.tasks.run_factor_scoring")
def run_factor_scoring() -> None:
    from agents.factor_library import score_ticker_factors
    from memory.database import AsyncSessionLocal, FactorScore

    async def _run() -> None:
        settings = get_settings()
        async with AsyncSessionLocal() as session:
            for ticker in settings.watchlist:
                scores = await score_ticker_factors(ticker)
                for s in scores:
                    session.add(FactorScore(ticker=ticker, **s))
            await session.commit()

    asyncio.run(_run())


# ── Phase 7 tasks ──────────────────────────────────────────────────────────────

@celery_app.task(name="scheduler.tasks.run_memory_agent")
def run_memory_agent() -> None:
    from agents.memory_agent import MemoryAgent
    asyncio.run(MemoryAgent().run())


@celery_app.task(name="scheduler.tasks.run_digest")
def run_digest() -> None:
    from intelligence.discord_notifier import send_digest_embed
    from intelligence.summarizer import build_digest

    async def _run() -> None:
        from intelligence.discord_notifier import send_message
        digest, count, signals, risk = await build_digest(hours=6)
        if count > 0:
            await send_digest_embed(digest, article_count=count, hours=6, signals=signals, risk=risk)
        else:
            await send_message("📭 No articles in the last 6h — run `!cycle` to fetch fresh news.")

    asyncio.run(_run())


# ── Beat schedule ──────────────────────────────────────────────────────────────

celery_app.conf.beat_schedule = {
    # Phase 2 — raw data collection
    "news-hunter": {
        "task": "scheduler.tasks.run_news_hunter",
        "schedule": float(_settings.news_poll_interval),      # 5 min
    },
    "market-watch": {
        "task": "scheduler.tasks.run_market_watch",
        "schedule": float(_settings.market_poll_interval),    # 1 min
    },
    # Phase 3 — intelligence
    "sentiment-analyst": {
        "task": "scheduler.tasks.run_sentiment_analyst",
        "schedule": float(_settings.news_poll_interval),      # after each news cycle
    },
    "risk-monitor": {
        "task": "scheduler.tasks.run_risk_monitor",
        "schedule": float(_settings.risk_poll_interval),      # 15 min
    },
    "research-analyst": {
        "task": "scheduler.tasks.run_research_analyst",
        "schedule": 3600.0,                                   # hourly deep dive
    },
    "digest": {
        "task": "scheduler.tasks.run_digest",
        "schedule": 21600.0,                                  # 6 hours
    },
    # Phase 7 — agent memory
    "memory-agent": {
        "task": "scheduler.tasks.run_memory_agent",
        "schedule": 86400.0,                                  # daily
    },
    # Financial analysis
    "financial-analyst": {
        "task": "scheduler.tasks.run_financial_analyst",
        "schedule": 86400.0,                                  # daily (financials update quarterly)
    },
    # Discovery
    "discovery-agent": {
        "task": "scheduler.tasks.run_discovery_agent",
        "schedule": 21600.0,                                  # every 6 hours (aligned with digest)
    },
    # Phase 8 — factor scoring
    "factor-scoring": {
        "task": "scheduler.tasks.run_factor_scoring",
        "schedule": crontab(hour=6, minute=0, day_of_week=1),  # Monday 06:00 UTC
    },
}
