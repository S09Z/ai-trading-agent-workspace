import asyncio

from celery import Celery

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


@celery_app.task(name="scheduler.tasks.run_digest")
def run_digest() -> None:
    from intelligence.discord_notifier import send_digest_embed
    from intelligence.summarizer import build_digest

    async def _run() -> None:
        digest, count, signals, risk = await build_digest(hours=6)
        if count > 0:
            await send_digest_embed(digest, article_count=count, hours=6, signals=signals, risk=risk)

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
}
