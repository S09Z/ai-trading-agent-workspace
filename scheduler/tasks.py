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
    worker_prefetch_multiplier=1,  # one task at a time per worker
)


@celery_app.task(name="scheduler.tasks.run_news_hunter")
def run_news_hunter() -> None:
    from agents.news_hunter import NewsHunterAgent
    asyncio.run(NewsHunterAgent().run())


@celery_app.task(name="scheduler.tasks.run_market_watch")
def run_market_watch() -> None:
    from agents.market_watch import MarketWatchAgent
    asyncio.run(MarketWatchAgent().run())


celery_app.conf.beat_schedule = {
    "news-hunter": {
        "task": "scheduler.tasks.run_news_hunter",
        "schedule": float(_settings.news_poll_interval),
    },
    "market-watch": {
        "task": "scheduler.tasks.run_market_watch",
        "schedule": float(_settings.market_poll_interval),
    },
}
