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


_SIGNAL_ICONS = {"bullish": "🟢", "bearish": "🔴", "watchlist": "🔬", "alert": "⚠️"}


def _format_intelligence_section(
    signals: list[dict] | None,
    risk: dict | None,
) -> str:
    """Build the Agent Intelligence section. Returns empty string if nothing to show."""
    lines: list[str] = []

    sentiment = [s for s in (signals or []) if s["signal_type"] in ("bullish", "bearish")]
    if sentiment:
        parts = [
            f"{s['ticker']} {_SIGNAL_ICONS[s['signal_type']]} {s['confidence']:.2f}"
            for s in sentiment[:5]
        ]
        lines.append("**🧠 Agent Intelligence**")
        lines.append("Signals: " + "  ".join(parts))

    research = next(
        (s for s in (signals or []) if s["signal_type"] == "watchlist" and s.get("rationale")),
        None,
    )
    if research:
        if not lines:
            lines.append("**🧠 Agent Intelligence**")
        lines.append(f"🔬 {research['ticker']}: {research['rationale'][:200]}")

    if risk and (risk.get("spike_count", 0) > 0 or risk.get("circuit_open") or risk.get("alert_count", 0) > 0):
        circuit = "🔴 OPEN" if risk.get("circuit_open") else "🟢 CLOSED"
        if not lines:
            lines.append("**🧠 Agent Intelligence**")
        lines.append(f"⚠️ Risk: {risk.get('spike_count', 0)} spikes (15min) | Circuit: {circuit}")

    return "\n".join(lines)


async def send_digest_embed(
    digest_text: str,
    article_count: int = 0,
    hours: int = 6,
    signals: list[dict] | None = None,
    risk: dict | None = None,
) -> None:
    """POST a rich embed containing the market digest to Discord."""
    meta = f"⏱ Last {hours}h  |  📄 {article_count} Articles  |  🤖 Murff Alpha"
    intel = _format_intelligence_section(signals, risk)
    body = f"{digest_text}\n\n{intel}" if intel else digest_text
    description = f"{_SEP}\n{body}\n{_SEP}\n{meta}"

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
