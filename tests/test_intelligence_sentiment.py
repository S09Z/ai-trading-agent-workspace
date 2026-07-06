"""Tests for the sentiment classifier — all LLM calls mocked."""

from unittest.mock import AsyncMock, patch

import pytest

# ── _parse ──────────────────────────────────────────────────────────────────

def test_parse_valid_bullish_json():
    from intelligence.sentiment import _parse

    result = _parse('{"sentiment": "bullish", "score": 0.8}')
    assert result["sentiment"] == "bullish"
    assert result["score"] == pytest.approx(0.8)


def test_parse_valid_bearish_json():
    from intelligence.sentiment import _parse

    result = _parse('{"sentiment": "bearish", "score": -0.75}')
    assert result["sentiment"] == "bearish"
    assert result["score"] == pytest.approx(-0.75)


def test_parse_clamps_score_above_one():
    from intelligence.sentiment import _parse

    result = _parse('{"sentiment": "bullish", "score": 2.5}')
    assert result["score"] == pytest.approx(1.0)


def test_parse_clamps_score_below_minus_one():
    from intelligence.sentiment import _parse

    result = _parse('{"sentiment": "bearish", "score": -5.0}')
    assert result["score"] == pytest.approx(-1.0)


def test_parse_handles_garbage_input():
    from intelligence.sentiment import _parse

    result = _parse("I cannot determine the sentiment of this article.")
    assert result["sentiment"] == "neutral"
    assert result["score"] == pytest.approx(0.0)


def test_parse_extracts_json_from_surrounding_text():
    from intelligence.sentiment import _parse

    result = _parse('Here is the answer: {"sentiment": "bullish", "score": 0.6} hope that helps!')
    assert result["sentiment"] == "bullish"
    assert result["score"] == pytest.approx(0.6)


# ── analyze_sentiment (LLM chokepoint) ──────────────────────────────────────

async def test_analyze_sentiment_returns_dict():
    from intelligence.sentiment import analyze_sentiment

    with patch("intelligence.llm.analyze", new=AsyncMock(
        return_value='{"sentiment": "bullish", "score": 0.9}'
    )):
        result = await analyze_sentiment("NVDA beats earnings", "Revenue up 80% YoY")

    assert result["sentiment"] == "bullish"
    assert result["score"] == pytest.approx(0.9)


async def test_analyze_sentiment_forwards_system_prompt():
    from intelligence.sentiment import _SYSTEM, analyze_sentiment

    mock_analyze = AsyncMock(return_value='{"sentiment": "neutral", "score": 0.0}')
    with patch("intelligence.llm.analyze", new=mock_analyze):
        await analyze_sentiment("Fed keeps rates unchanged")

    assert mock_analyze.call_args.kwargs["system"] == _SYSTEM


# ── analyze_sentiment (local path) ──────────────────────────────────────────

async def test_analyze_sentiment_uses_local_client_when_configured():
    from intelligence.sentiment import analyze_sentiment

    with patch("intelligence.sentiment._settings") as s, \
         patch("intelligence.local_client.chat_local", new=AsyncMock(
             return_value='{"sentiment": "bearish", "score": -0.6}'
         )):
        s.use_local_llm = True
        result = await analyze_sentiment("Layoffs announced at major tech firm")

    assert result["sentiment"] == "bearish"
