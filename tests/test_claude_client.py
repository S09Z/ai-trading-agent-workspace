"""Tests for the Claude API client wrapper.

All tests mock intelligence.claude_client._client so no real API calls are made.
The mock_claude fixture is defined in conftest.py.
"""

from unittest.mock import AsyncMock, patch

import pytest

from intelligence.claude_client import analyze, chat

# ── analyze ────────────────────────────────────────────────────────────────────

async def test_analyze_returns_text(mock_claude):
    result = await analyze("Summarise this market event.")
    assert result == "OK"


async def test_analyze_calls_api_once(mock_claude):
    await analyze("What is the sentiment?")
    mock_claude.messages.create.assert_called_once()


async def test_analyze_without_context_sends_prompt_directly(mock_claude):
    await analyze("Is NVDA bullish?")
    call_kwargs = mock_claude.messages.create.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    assert content == "Is NVDA bullish?"


async def test_analyze_with_context_prepends_context(mock_claude):
    await analyze("What is the sentiment?", context="NVDA up 5% after earnings.")
    call_kwargs = mock_claude.messages.create.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    assert "NVDA up 5% after earnings." in content
    assert "What is the sentiment?" in content
    assert content.index("NVDA up 5%") < content.index("What is the sentiment?")


async def test_analyze_passes_max_tokens(mock_claude):
    await analyze("Brief summary.", max_tokens=256)
    call_kwargs = mock_claude.messages.create.call_args.kwargs
    assert call_kwargs["max_tokens"] == 256


# ── chat ───────────────────────────────────────────────────────────────────────

async def test_chat_returns_message_object(mock_claude):
    messages = [{"role": "user", "content": "Hello"}]
    response = await chat(messages)
    assert response.content[0].text == "OK"


async def test_chat_system_prompt_uses_cache_control(mock_claude):
    """System prompt must include cache_control for prompt caching."""
    await chat(
        messages=[{"role": "user", "content": "analyse this"}],
        system="You are a senior equity analyst.",
    )
    call_kwargs = mock_claude.messages.create.call_args.kwargs
    system_blocks = call_kwargs["system"]
    assert len(system_blocks) == 1
    assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert system_blocks[0]["text"] == "You are a senior equity analyst."


async def test_chat_without_system_sends_no_system_key(mock_claude):
    await chat(messages=[{"role": "user", "content": "hello"}])
    call_kwargs = mock_claude.messages.create.call_args.kwargs
    assert "system" not in call_kwargs


async def test_chat_passes_tools_to_api(mock_claude):
    tools = [
        {
            "name": "get_price",
            "description": "Fetch the current price for a ticker.",
            "input_schema": {"type": "object", "properties": {"ticker": {"type": "string"}}},
        }
    ]
    await chat(messages=[{"role": "user", "content": "What is AAPL trading at?"}], tools=tools)
    call_kwargs = mock_claude.messages.create.call_args.kwargs
    assert call_kwargs["tools"] == tools


async def test_chat_without_tools_sends_no_tools_key(mock_claude):
    await chat(messages=[{"role": "user", "content": "hello"}])
    call_kwargs = mock_claude.messages.create.call_args.kwargs
    assert "tools" not in call_kwargs


async def test_chat_uses_configured_model(mock_claude):
    from config.settings import get_settings
    model = get_settings().claude_model

    await chat(messages=[{"role": "user", "content": "test"}])
    call_kwargs = mock_claude.messages.create.call_args.kwargs
    assert call_kwargs["model"] == model


async def test_analyze_propagates_api_error():
    """If the API raises, analyze() should let the exception bubble up."""
    with patch("intelligence.claude_client._client") as mock_client:
        mock_client.messages.create = AsyncMock(side_effect=RuntimeError("API down"))
        with pytest.raises(RuntimeError, match="API down"):
            await analyze("test")
