"""Tests for the Discord notifier (Bot token REST API).

All HTTP calls are mocked — no real requests sent.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_CHANNEL_ID = "111222333444555666"
_TOKEN = "test-bot-token"
_CLIENT_PATCH = "intelligence.discord_notifier.httpx.AsyncClient"
_SETTINGS_PATCH = "intelligence.discord_notifier._settings"


def _mock_client():
    """Build an AsyncClient context manager that captures POST calls."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_post = AsyncMock(return_value=mock_response)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=MagicMock(post=mock_post))
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, mock_post


def _mock_settings(token=_TOKEN, channel_id=_CHANNEL_ID):
    s = MagicMock()
    s.discord_bot_token = token
    s.discord_digest_channel_id = channel_id
    return s


@pytest.fixture
def discord_mock():
    """Patch settings + httpx client for all notifier tests."""
    ctx, mock_post = _mock_client()
    with patch(_SETTINGS_PATCH, _mock_settings()), patch(_CLIENT_PATCH, return_value=ctx):
        yield mock_post


# ── send_message ───────────────────────────────────────────────────────────────

async def test_send_message_posts_content(discord_mock):
    from intelligence.discord_notifier import send_message

    await send_message("Hello from AlphaOps")

    discord_mock.assert_called_once()
    payload = discord_mock.call_args.kwargs["json"]
    assert payload["content"] == "Hello from AlphaOps"


async def test_send_message_posts_to_digest_channel(discord_mock):
    from intelligence.discord_notifier import send_message

    await send_message("ping")

    url = discord_mock.call_args.args[0]
    assert _CHANNEL_ID in url


async def test_send_message_uses_bot_auth_header(discord_mock):
    from intelligence.discord_notifier import send_message

    await send_message("ping")

    headers = discord_mock.call_args.kwargs["headers"]
    assert headers["Authorization"] == f"Bot {_TOKEN}"


async def test_send_message_raises_without_token():
    from intelligence.discord_notifier import send_message

    with patch(_SETTINGS_PATCH, _mock_settings(token="")):
        with pytest.raises(ValueError, match="DISCORD_BOT_TOKEN"):
            await send_message("test")


async def test_send_message_raises_without_channel_id():
    from intelligence.discord_notifier import send_message

    with patch(_SETTINGS_PATCH, _mock_settings(channel_id="")):
        with pytest.raises(ValueError, match="DISCORD_DIGEST_CHANNEL_ID"):
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
    assert "42" in embed["description"]


async def test_send_digest_embed_description_contains_digest_text(discord_mock):
    from intelligence.discord_notifier import send_digest_embed

    await send_digest_embed("NVDA is bullish.", article_count=3)

    embed = discord_mock.call_args.kwargs["json"]["embeds"][0]
    assert "NVDA is bullish." in embed["description"]


async def test_send_digest_embed_has_timestamp(discord_mock):
    from intelligence.discord_notifier import send_digest_embed

    await send_digest_embed("Test", article_count=1)

    embed = discord_mock.call_args.kwargs["json"]["embeds"][0]
    assert "timestamp" in embed


async def test_send_digest_embed_posts_to_digest_channel(discord_mock):
    from intelligence.discord_notifier import send_digest_embed

    await send_digest_embed("Test", article_count=1)

    url = discord_mock.call_args.args[0]
    assert _CHANNEL_ID in url


# ── _format_intelligence_section ──────────────────────────────────────────────

def test_format_intelligence_section_empty_when_no_data():
    from intelligence.discord_notifier import _format_intelligence_section

    assert _format_intelligence_section(None, None) == ""
    assert _format_intelligence_section([], {"spike_count": 0, "circuit_open": False, "alert_count": 0}) == ""


def test_format_intelligence_section_shows_sentiment_signals():
    from intelligence.discord_notifier import _format_intelligence_section

    signals = [
        {"ticker": "CRM", "signal_type": "bullish", "confidence": 0.82, "rationale": None},
        {"ticker": "TSLA", "signal_type": "bearish", "confidence": 0.71, "rationale": None},
    ]
    result = _format_intelligence_section(signals, None)
    assert "CRM" in result
    assert "🟢" in result
    assert "TSLA" in result
    assert "🔴" in result


def test_format_intelligence_section_shows_research():
    from intelligence.discord_notifier import _format_intelligence_section

    signals = [
        {"ticker": "NVDA", "signal_type": "watchlist", "confidence": 0.5, "rationale": "Strong thesis here."},
    ]
    result = _format_intelligence_section(signals, None)
    assert "🔬" in result
    assert "NVDA" in result
    assert "Strong thesis here." in result


def test_format_intelligence_section_shows_risk_when_spikes():
    from intelligence.discord_notifier import _format_intelligence_section

    risk = {"spike_count": 3, "circuit_open": False, "alert_count": 0}
    result = _format_intelligence_section([], risk)
    assert "⚠️" in result
    assert "3" in result


def test_format_intelligence_section_circuit_open():
    from intelligence.discord_notifier import _format_intelligence_section

    risk = {"spike_count": 0, "circuit_open": True, "alert_count": 0}
    result = _format_intelligence_section([], risk)
    assert "🔴 OPEN" in result


async def test_send_digest_embed_includes_intelligence_section(discord_mock):
    from intelligence.discord_notifier import send_digest_embed

    signals = [{"ticker": "AAPL", "signal_type": "bullish", "confidence": 0.75, "rationale": None}]
    risk = {"spike_count": 1, "circuit_open": False, "alert_count": 0}

    await send_digest_embed("Digest text", article_count=5, signals=signals, risk=risk)

    desc = discord_mock.call_args.kwargs["json"]["embeds"][0]["description"]
    assert "🧠 Agent Intelligence" in desc
    assert "AAPL" in desc
    assert "⚠️" in desc
