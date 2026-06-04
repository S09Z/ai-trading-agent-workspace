"""Tests for Discord bot: connection, channel availability, channel filter, and commands.

All Discord and Celery calls are mocked — no real connections made.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_SETTINGS_PATCH = "intelligence.discord_bot._settings"
_CELERY_PING_PATCH = "intelligence.discord_bot._queue.__code__"
_BOT_TOKEN = "test-bot-token"
_DIGEST_CHANNEL_ID = "111111111111111111"
_BOT_CHANNEL_ID = "222222222222222222"

# Simulates a live Celery worker responding to ping
_MOCK_PING = patch("scheduler.tasks.celery_app.control.ping", return_value=[{"worker@host": {"ok": "pong"}}])


def _make_settings(
    token: str = _BOT_TOKEN,
    digest_id: str = _DIGEST_CHANNEL_ID,
    bot_id: str = _BOT_CHANNEL_ID,
) -> MagicMock:
    s = MagicMock()
    s.discord_bot_token = token
    s.discord_digest_channel_id = digest_id
    s.discord_bot_channel_id = bot_id
    return s


def _make_ctx(channel_id: str = _BOT_CHANNEL_ID) -> MagicMock:
    ctx = MagicMock()
    ctx.channel.id = int(channel_id)
    ctx.reply = AsyncMock()
    return ctx


# ── Connection ─────────────────────────────────────────────────────────────────

def test_main_raises_when_token_missing():
    """main() raises RuntimeError if DISCORD_BOT_TOKEN is empty."""
    from intelligence.discord_bot import main

    with patch(_SETTINGS_PATCH, _make_settings(token="")):
        with pytest.raises(RuntimeError, match="DISCORD_BOT_TOKEN"):
            main()


def test_main_calls_bot_run_with_token():
    """main() passes the configured token to bot.run()."""
    from intelligence.discord_bot import main

    with patch(_SETTINGS_PATCH, _make_settings()), \
         patch("intelligence.discord_bot.bot.run") as mock_run:
        main()

    mock_run.assert_called_once_with(_BOT_TOKEN)


# ── Channel availability ───────────────────────────────────────────────────────

async def test_digest_channel_sends_to_correct_channel():
    """Notifier POSTs to the URL that contains DISCORD_DIGEST_CHANNEL_ID."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_post = AsyncMock(return_value=mock_resp)
    ctx_mgr = AsyncMock()
    ctx_mgr.__aenter__ = AsyncMock(return_value=MagicMock(post=mock_post))
    ctx_mgr.__aexit__ = AsyncMock(return_value=False)

    notifier_settings = MagicMock()
    notifier_settings.discord_bot_token = _BOT_TOKEN
    notifier_settings.discord_digest_channel_id = _DIGEST_CHANNEL_ID

    with patch("intelligence.discord_notifier._settings", notifier_settings), \
         patch("intelligence.discord_notifier.httpx.AsyncClient", return_value=ctx_mgr):
        from intelligence.discord_notifier import send_message
        await send_message("channel check")

    url = mock_post.call_args.args[0]
    assert _DIGEST_CHANNEL_ID in url, f"Expected digest channel ID in URL, got: {url}"


async def test_send_message_raises_when_digest_channel_not_configured():
    """Notifier raises ValueError if DISCORD_DIGEST_CHANNEL_ID is empty."""
    notifier_settings = MagicMock()
    notifier_settings.discord_bot_token = _BOT_TOKEN
    notifier_settings.discord_digest_channel_id = ""

    with patch("intelligence.discord_notifier._settings", notifier_settings):
        from intelligence.discord_notifier import send_message
        with pytest.raises(ValueError, match="DISCORD_DIGEST_CHANNEL_ID"):
            await send_message("test")


async def test_send_digest_embed_raises_when_digest_channel_not_configured():
    """send_digest_embed raises ValueError if DISCORD_DIGEST_CHANNEL_ID is empty."""
    notifier_settings = MagicMock()
    notifier_settings.discord_bot_token = _BOT_TOKEN
    notifier_settings.discord_digest_channel_id = ""

    with patch("intelligence.discord_notifier._settings", notifier_settings):
        from intelligence.discord_notifier import send_digest_embed
        with pytest.raises(ValueError, match="DISCORD_DIGEST_CHANNEL_ID"):
            await send_digest_embed("test", article_count=1)


# ── Channel filter (global check) ─────────────────────────────────────────────

async def test_channel_check_allows_bot_channel():
    """_check_channel returns True for DISCORD_BOT_CHANNEL_ID."""
    from intelligence.discord_bot import _check_channel

    ctx = _make_ctx(channel_id=_BOT_CHANNEL_ID)
    with patch(_SETTINGS_PATCH, _make_settings()):
        result = await _check_channel(ctx)

    assert result is True


async def test_channel_check_blocks_other_channels():
    """_check_channel returns False for any channel that is not DISCORD_BOT_CHANNEL_ID."""
    from intelligence.discord_bot import _check_channel

    ctx = _make_ctx(channel_id="999999999999999999")
    with patch(_SETTINGS_PATCH, _make_settings()):
        result = await _check_channel(ctx)

    assert result is False


async def test_channel_check_allows_all_when_bot_channel_not_configured():
    """If DISCORD_BOT_CHANNEL_ID is empty, bot responds in every channel (dev mode)."""
    from intelligence.discord_bot import _check_channel

    ctx = _make_ctx(channel_id="999999999999999999")
    with patch(_SETTINGS_PATCH, _make_settings(bot_id="")):
        result = await _check_channel(ctx)

    assert result is True


# ── Commands ───────────────────────────────────────────────────────────────────

async def test_cmd_cycle_triggers_three_tasks():
    """!cycle dispatches news, sentiment, and risk tasks to Celery."""
    from intelligence.discord_bot import cmd_cycle

    ctx = _make_ctx()
    mock_news = MagicMock()
    mock_sentiment = MagicMock()
    mock_risk = MagicMock()

    with _MOCK_PING, \
         patch("scheduler.tasks.run_news_hunter", mock_news), \
         patch("scheduler.tasks.run_sentiment_analyst", mock_sentiment), \
         patch("scheduler.tasks.run_risk_monitor", mock_risk):
        await cmd_cycle(ctx)

    mock_news.apply_async.assert_called_once()
    mock_sentiment.apply_async.assert_called_once()
    mock_risk.apply_async.assert_called_once()
    ctx.reply.assert_awaited_once()


async def test_cmd_cycle_replies_confirmation():
    from intelligence.discord_bot import cmd_cycle

    ctx = _make_ctx()
    with _MOCK_PING, \
         patch("scheduler.tasks.run_news_hunter", MagicMock()), \
         patch("scheduler.tasks.run_sentiment_analyst", MagicMock()), \
         patch("scheduler.tasks.run_risk_monitor", MagicMock()):
        await cmd_cycle(ctx)

    assert "✅" in ctx.reply.call_args.args[0]


async def test_cmd_digest_triggers_task():
    """!digest dispatches the digest task to Celery."""
    from intelligence.discord_bot import cmd_digest

    ctx = _make_ctx()
    mock_task = MagicMock()

    with _MOCK_PING, patch("scheduler.tasks.run_digest", mock_task):
        await cmd_digest(ctx)

    mock_task.apply_async.assert_called_once()
    ctx.reply.assert_awaited_once()


async def test_cmd_research_with_ticker_triggers_task():
    """!research NVDA dispatches research task with uppercased ticker."""
    from intelligence.discord_bot import cmd_research

    ctx = _make_ctx()
    mock_task = MagicMock()

    with _MOCK_PING, patch("scheduler.tasks.run_research_analyst", mock_task):
        await cmd_research(ctx, ticker="nvda")

    mock_task.apply_async.assert_called_once_with(kwargs={"ticker": "NVDA"}, ignore_result=True)
    assert "NVDA" in ctx.reply.call_args.args[0]


async def test_cmd_research_without_ticker_replies_usage():
    """!research with no ticker replies with usage instructions."""
    from intelligence.discord_bot import cmd_research

    ctx = _make_ctx()
    await cmd_research(ctx, ticker="")

    ctx.reply.assert_awaited_once()
    assert "Usage" in ctx.reply.call_args.args[0]


async def test_cmd_research_without_ticker_does_not_trigger_task():
    """!research with no ticker must NOT dispatch any Celery task."""
    from intelligence.discord_bot import cmd_research

    ctx = _make_ctx()
    mock_task = MagicMock()

    with patch("scheduler.tasks.run_research_analyst", mock_task):
        await cmd_research(ctx, ticker="")

    mock_task.delay.assert_not_called()


async def test_cmd_status_includes_all_agents():
    """!status reply mentions every agent by name."""
    from intelligence.discord_bot import cmd_status

    ctx = _make_ctx()
    await cmd_status(ctx)

    reply = ctx.reply.call_args.args[0]
    for agent in ("NewsHunter", "MarketWatch", "SentimentAnalyst", "RiskMonitor", "ResearchAnalyst", "Digest"):
        assert agent in reply, f"Expected '{agent}' in status reply"


async def test_cmd_help_alpha_lists_all_commands():
    """!help_alpha reply mentions every available command."""
    from intelligence.discord_bot import cmd_help

    ctx = _make_ctx()
    await cmd_help(ctx)

    reply = ctx.reply.call_args.args[0]
    for cmd in ("!cycle", "!digest", "!research", "!status"):
        assert cmd in reply, f"Expected '{cmd}' in help reply"
