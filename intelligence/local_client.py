"""Ollama local inference client — drop-in alternative to Claude for the digest."""

import re

import httpx

from config.settings import get_settings

_settings = get_settings()

# Strips <think>...</think> blocks that qwen3 and deepseek-r1 emit in thinking mode
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_thinking(text: str) -> str:
    return _THINK_RE.sub("", text).strip()


async def chat_local(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """Send a prompt to the local Ollama instance and return the response text.

    Thinking mode is disabled so qwen3 / deepseek-r1 return clean text directly.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"{_settings.ollama_url}/api/chat",
            json={
                "model": _settings.local_model,
                "messages": messages,
                "stream": False,
                "think": False,          # disable qwen3/deepseek thinking mode
                "options": {"num_predict": max_tokens},
            },
        )
        r.raise_for_status()
        content = r.json()["message"]["content"]
        return _strip_thinking(content)  # safety-strip in case think:false is ignored
