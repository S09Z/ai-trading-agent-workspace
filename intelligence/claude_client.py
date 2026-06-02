from anthropic import AsyncAnthropic
from anthropic.types import Message

from config.settings import get_settings

_settings = get_settings()
_client = AsyncAnthropic(api_key=_settings.anthropic_api_key)


async def chat(
    messages: list[dict],
    system: str = "",
    tools: list[dict] | None = None,
    max_tokens: int = 2048,
) -> Message:
    """Send a conversation to Claude. Caches the system prompt to reduce token costs."""
    kwargs: dict = {
        "model": _settings.claude_model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]
    if tools:
        kwargs["tools"] = tools

    return await _client.messages.create(**kwargs)


async def analyze(prompt: str, context: str = "", max_tokens: int = 1024) -> str:
    """Single-turn analysis — returns Claude's response text."""
    content = f"Context:\n{context}\n\n{prompt}" if context else prompt
    response = await chat(
        messages=[{"role": "user", "content": content}],
        max_tokens=max_tokens,
    )
    return response.content[0].text
