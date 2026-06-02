"""Send messages and rich embeds to a Discord channel via webhook."""

from datetime import UTC, datetime

import httpx

from config.settings import get_settings

_settings = get_settings()

_EMBED_COLOR = 0x044104  # AlphaOps green
_SEP = "─" * 35


def _webhook_url() -> str:
    if not _settings.discord_webhook_url:
        raise ValueError(
            "DISCORD_WEBHOOK_URL is not set in .env. "
            "Get it from: Discord channel → Edit Channel → Integrations → Webhooks."
        )
    return _settings.discord_webhook_url


async def send_message(content: str) -> None:
    """POST a plain-text message to the configured Discord webhook."""
    async with httpx.AsyncClient() as client:
        r = await client.post(_webhook_url(), json={"content": content}, timeout=10)
        r.raise_for_status()


async def send_digest_embed(digest_text: str, article_count: int = 0, hours: int = 6) -> None:
    """POST a rich embed containing the market digest to Discord."""
    meta = f"⏱ Last {hours}h  |  📄 {article_count} Articles  |  🤖 Murff Alpha"
    description = f"{_SEP}\n{digest_text}\n{_SEP}\n{meta}"

    embed = {
        "title": "📰 AlphaOps — Market Digest",
        "description": description,
        "color": _EMBED_COLOR,
        "footer": {"text": "AlphaOps — powered by Claude"},
        "timestamp": datetime.now(UTC).isoformat(),
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(_webhook_url(), json={"embeds": [embed]}, timeout=10)
        r.raise_for_status()
