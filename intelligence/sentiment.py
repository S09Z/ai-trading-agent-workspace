"""Sentiment classification for news articles — routes to Claude or local Ollama."""

import json
import re

from config.settings import get_settings

_settings = get_settings()

_SYSTEM = """\
You are a financial sentiment classifier.
Analyse the news article and return ONLY valid JSON — no other text:
{"sentiment": "bullish"|"bearish"|"neutral", "score": <float -1.0 to 1.0>}

Rules:
- bullish  → positive for markets/company (beat estimates, expansion, strong demand)
- bearish  → negative for markets/company (miss, layoffs, regulatory risk, crisis)
- neutral  → no clear directional market impact
- score    → -1.0 very bearish … 0.0 neutral … 1.0 very bullish\
"""


def _parse(raw: str) -> dict:
    """Extract JSON from model response. Returns neutral fallback on failure."""
    try:
        match = re.search(r"\{[^}]+\}", raw)
        if match:
            data = json.loads(match.group())
            sentiment = data.get("sentiment", "neutral")
            score = float(data.get("score", 0.0))
            return {"sentiment": sentiment, "score": max(-1.0, min(1.0, score))}
    except Exception:
        pass
    return {"sentiment": "neutral", "score": 0.0}


async def analyze_sentiment(title: str, content: str = "") -> dict:
    """Classify article sentiment. Returns {"sentiment": str, "score": float}."""
    body = content[:500] if content else ""
    prompt = f"Title: {title}\n\nContent: {body or '(none)'}"

    from intelligence.llm import analyze
    raw = await analyze(prompt, system=_SYSTEM, max_tokens=60)

    return _parse(raw)
