"""Unified LLM dispatch — Groq → Ollama → Claude (priority order)."""

from config.settings import get_settings


async def analyze(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    settings = get_settings()
    if settings.use_groq:
        from intelligence.groq_client import analyze as _fn
        return await _fn(prompt, system=system, max_tokens=max_tokens)
    if settings.use_local_llm:
        from intelligence.local_client import chat_local
        return await chat_local(prompt, system=system, max_tokens=max_tokens)
    from intelligence.claude_client import analyze as _fn
    return await _fn(prompt, max_tokens=max_tokens)
