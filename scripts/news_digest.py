"""News digest script — summarise recent articles and post to Discord.

Usage:
    uv run python -m scripts.news_digest              # fetch, summarise, post
    uv run python -m scripts.news_digest --dry-run    # print without posting
    uv run python -m scripts.news_digest --hours 12   # extend lookback window
    uv run poe digest                                 # shortcut (default 6h)
"""

import argparse
import asyncio
import sys


async def run(hours: int, dry_run: bool) -> None:
    from config.settings import get_settings
    from intelligence.discord_notifier import send_digest_embed
    from intelligence.summarizer import build_digest

    settings = get_settings()
    backend = f"Ollama ({settings.local_model})" if settings.use_local_llm else "Claude"

    print(f"Fetching articles and signals from the last {hours}h...")
    digest, count, signals, risk = await build_digest(hours=hours)

    if count == 0:
        print("Nothing to summarise. Run 'make start' to verify DB, then let NewsHunter collect.")
        return

    print(f"Found {count} article(s), {len(signals)} signal(s). Generating digest with {backend}...\n")

    print("─" * 60)
    print(digest)
    print("─" * 60)

    if dry_run:
        print("\n[dry-run] Discord post skipped.")
        return

    print("\nPosting to Discord...")
    try:
        await send_digest_embed(digest, article_count=count, hours=hours, signals=signals, risk=risk)
        print("✓ Posted successfully.")
    except ValueError as exc:
        print(f"✗ {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"✗ Discord error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AlphaOps news digest")
    parser.add_argument("--dry-run", action="store_true", help="Print without posting to Discord")
    parser.add_argument("--hours", type=int, default=6, help="Lookback window in hours (default 6)")
    args = parser.parse_args()
    asyncio.run(run(hours=args.hours, dry_run=args.dry_run))
