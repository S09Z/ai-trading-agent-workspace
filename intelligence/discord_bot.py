"""Discord bot — receives commands and triggers agent tasks via Celery."""

import logging

import discord
from discord.ext import commands

from config.settings import get_settings

_settings = get_settings()
_log = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True  # required to read message text

bot = commands.Bot(command_prefix="!", intents=intents)


async def _check_channel(ctx: commands.Context) -> bool:
    """Global check — only respond in DISCORD_BOT_CHANNEL_ID."""
    allowed = _settings.discord_bot_channel_id
    if allowed and str(ctx.channel.id) != allowed:
        return False
    return True

bot.add_check(_check_channel)


@bot.event
async def on_ready() -> None:
    """Log a confirmation message once the bot has connected to Discord."""
    _log.info("Discord bot ready: %s", bot.user)


def _queue(task, **kwargs) -> None:
    """Queue a Celery task. Raises RuntimeError if broker or worker is unavailable."""
    from scheduler.tasks import celery_app
    try:
        workers = celery_app.control.ping(timeout=1.0)
    except Exception as exc:
        raise RuntimeError(f"Cannot reach Redis broker: {exc}") from exc
    if not workers:
        raise RuntimeError("No Celery workers are running")
    task.apply_async(kwargs=kwargs or None, ignore_result=True)


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception) -> None:
    """Reply with a user-friendly message on command failure."""
    if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
        return
    cause = getattr(error, "original", error)
    if isinstance(cause, RuntimeError):
        await ctx.reply(
            f"Service unavailable — {cause}\n"
            "Run: `docker compose up -d redis` and `celery -A scheduler.tasks:celery_app worker`"
        )
    else:
        _log.exception("Unhandled command error in %s", ctx.command)
        await ctx.reply(f"Unexpected error: {cause}")


@bot.command(name="cycle")
async def cmd_cycle(ctx: commands.Context) -> None:
    """Trigger full agent cycle: news → sentiment → risk → research."""
    from scheduler.tasks import run_news_hunter, run_sentiment_analyst, run_risk_monitor
    _queue(run_news_hunter)
    _queue(run_sentiment_analyst)
    _queue(run_risk_monitor)
    await ctx.reply("Agent cycle started ✅")


@bot.command(name="digest")
async def cmd_digest(ctx: commands.Context) -> None:
    """Generate and post the market digest now."""
    from scheduler.tasks import run_digest
    _queue(run_digest)
    await ctx.reply("Digest queued — posting to digest channel in ~1 min ✅")


@bot.command(name="research")
async def cmd_research(ctx: commands.Context, ticker: str = "") -> None:
    """Run deep research on a ticker. Usage: !research NVDA"""
    if not ticker:
        await ctx.reply("Usage: `!research TICKER`  e.g. `!research NVDA`")
        return
    from scheduler.tasks import run_research_analyst
    _queue(run_research_analyst, ticker=ticker.upper())
    await ctx.reply(f"Research on **{ticker.upper()}** queued ✅")


@bot.command(name="status")
async def cmd_status(ctx: commands.Context) -> None:
    """Show agent schedule."""
    lines = [
        "**AlphaOps — Agent Schedule**",
        "```",
        "NewsHunter       every 5 min",
        "MarketWatch      every 1 min",
        "SentimentAnalyst every 5 min",
        "RiskMonitor      every 15 min",
        "ResearchAnalyst  every 1 h",
        "Digest           every 6 h",
        "```",
    ]
    await ctx.reply("\n".join(lines))


@bot.command(name="help_alpha")
async def cmd_help(ctx: commands.Context) -> None:
    """Show available commands."""
    lines = [
        "**AlphaOps Commands**",
        "`!cycle` — trigger news → sentiment → risk pipeline",
        "`!digest` — generate market digest now",
        "`!research TICKER` — deep-dive on a ticker (e.g. `!research NVDA`)",
        "`!status` — show agent schedule",
    ]
    await ctx.reply("\n".join(lines))


def main() -> None:
    """Configure logging and start the Discord bot (blocking)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    token = _settings.discord_bot_token
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set in .env")
    bot.run(token)


if __name__ == "__main__":
    main()
