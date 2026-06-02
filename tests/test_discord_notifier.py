"""Tests for the Discord webhook notifier.

All HTTP calls are mocked — no real requests sent.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_WEBHOOK = "https://discord.com/api/webhooks/test/token"
_URL_PATCH = "intelligence.discord_notifier._webhook_url"
_CLIENT_PATCH = "intelligence.discord_notifier.httpx.AsyncClient"


def _mock_client():
    """Build an AsyncClient context manager that returns a no-op response."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_post = AsyncMock(return_value=mock_response)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=MagicMock(post=mock_post))
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_post


@pytest.fixture
def discord_mock():
    """Patch webhook URL + httpx client for all notifier tests."""
    ctx, mock_post = _mock_client()
    with patch(_URL_PATCH, return_value=_WEBHOOK), patch(_CLIENT_PATCH, return_value=ctx):
        yield mock_post


# ── send_message ───────────────────────────────────────────────────────────────

async def test_send_message_posts_content(discord_mock):
    from intelligence.discord_notifier import send_message

    await send_message("Hello from AlphaOps")

    discord_mock.assert_called_once()
    payload = discord_mock.call_args.kwargs["json"]
    assert payload["content"] == "Hello from AlphaOps"


async def test_send_message_raises_without_webhook():
    from intelligence.discord_notifier import send_message

    with patch("intelligence.discord_notifier._settings") as s:
        s.discord_webhook_url = ""
        with pytest.raises(ValueError, match="DISCORD_WEBHOOK_URL"):
            await send_message("test")


# ── send_digest_embed ──────────────────────────────────────────────────────────

async def test_send_digest_embed_posts_one_embed(discord_mock):
    from intelligence.discord_notifier import send_digest_embed

    await send_digest_embed("Market is bullish today.", article_count=12, hours=6)

    discord_mock.assert_called_once()
    embeds = discord_mock.call_args.kwargs["json"]["embeds"]
    assert len(embeds) == 1


async def test_send_digest_embed_title_contains_alphaops(discord_mock):
    from intelligence.discord_notifier import send_digest_embed

    await send_digest_embed("Test digest", article_count=5)

    embed = discord_mock.call_args.kwargs["json"]["embeds"][0]
    assert "AlphaOps" in embed["title"]


async def test_send_digest_embed_includes_article_count(discord_mock):
    from intelligence.discord_notifier import send_digest_embed

    await send_digest_embed("Digest text", article_count=42)

    embed = discord_mock.call_args.kwargs["json"]["embeds"][0]
    field_values = [f["value"] for f in embed["fields"]]
    assert "42" in field_values


async def test_send_digest_embed_description_is_digest_text(discord_mock):
    from intelligence.discord_notifier import send_digest_embed

    await send_digest_embed("NVDA is bullish.", article_count=3)

    embed = discord_mock.call_args.kwargs["json"]["embeds"][0]
    assert embed["description"] == "NVDA is bullish."


async def test_send_digest_embed_has_timestamp(discord_mock):
    from intelligence.discord_notifier import send_digest_embed

    await send_digest_embed("Test", article_count=1)

    embed = discord_mock.call_args.kwargs["json"]["embeds"][0]
    assert "timestamp" in embed
