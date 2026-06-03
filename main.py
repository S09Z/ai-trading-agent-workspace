"""Startup script — initializes all services and verifies connectivity."""

import asyncio
import sys


async def startup() -> None:
    print("AlphaOps — Phase 1 startup\n")

    # ── Database ───────────────────────────────────────────────────────────────
    print("  [1/3] Database...")
    try:
        from memory.database import init_db
        await init_db()
        print("        OK — tables created, hypertable ready")
    except Exception as e:
        print(f"        FAIL — {e}")
        sys.exit(1)

    # ── Vector store ───────────────────────────────────────────────────────────
    print("  [2/3] Qdrant vector store...")
    try:
        from memory.vector_store import ensure_collection
        await ensure_collection()
        print("        OK — collection ready")
    except Exception as e:
        print(f"        FAIL — {e}")
        sys.exit(1)

    # ── LLM connectivity ───────────────────────────────────────────────────────
    from config.settings import get_settings
    settings = get_settings()
    if settings.use_local_llm:
        print(f"  [3/3] Ollama ({settings.local_model})...")
        try:
            from intelligence.local_client import chat_local
            reply = await chat_local("Reply with exactly: OK", max_tokens=10)
            print(f"        OK — response: {reply.strip()}")
        except Exception as e:
            print(f"        FAIL — {e}")
            sys.exit(1)
    else:
        print("  [3/3] Claude API...")
        try:
            from intelligence.claude_client import analyze
            reply = await analyze("Reply with exactly: OK")
            print(f"        OK — response: {reply.strip()}")
        except Exception as e:
            print(f"        FAIL — {e}")
            sys.exit(1)

    print("\nAll systems ready.")


if __name__ == "__main__":
    asyncio.run(startup())
