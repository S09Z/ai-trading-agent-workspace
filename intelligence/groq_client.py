"""Groq cloud inference — OpenAI-compatible API, fast free tier."""

import httpx

from config.settings import get_settings

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


async def analyze(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    settings = get_settings()
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            _GROQ_URL,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={
                "model": settings.groq_model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.1,
            },
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
