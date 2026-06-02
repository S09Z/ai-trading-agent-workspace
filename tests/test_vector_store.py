"""Tests for Qdrant vector store against a real Qdrant instance.

Uses the 'alphaops_test' collection (created/destroyed in conftest.py).
Each test uses unique doc IDs so tests don't interfere with each other
within the same session.
"""

import uuid

import pytest

from memory.vector_store import search, upsert, upsert_batch

# All tests in this module require the Qdrant test collection to be set up.
pytestmark = pytest.mark.usefixtures("qdrant_test_collection")


def _uid() -> str:
    """Generate a UUID string suitable as a Qdrant point ID."""
    return str(uuid.uuid4())


# ── upsert ─────────────────────────────────────────────────────────────────────

async def test_upsert_stores_document():
    doc_id = _uid()
    await upsert(doc_id, "NVDA reports record GPU sales in Q4", {"ticker": "NVDA", "source": "test"})

    results = await search("NVIDIA quarterly revenue", limit=5)
    ids = [r.get("source") for r in results]
    assert "test" in ids


async def test_upsert_is_idempotent():
    """Re-inserting the same doc_id should update, not create a duplicate."""
    doc_id = _uid()
    await upsert(doc_id, "Apple launches new iPhone", {"ticker": "AAPL", "version": 1})
    await upsert(doc_id, "Apple launches new iPhone", {"ticker": "AAPL", "version": 2})

    results = await search("Apple iPhone launch", limit=10)
    matching = [r for r in results if r.get("ticker") == "AAPL" and r.get("version") == 2]
    # version 1 should have been replaced
    not_v1 = [r for r in results if r.get("ticker") == "AAPL" and r.get("version") == 1]

    assert len(matching) >= 1
    assert len(not_v1) == 0


async def test_upsert_stores_full_payload():
    doc_id = _uid()
    payload = {"ticker": "TSLA", "sentiment": "bullish", "score": 0.9, "source": "reuters"}
    await upsert(doc_id, "Tesla deliveries exceed expectations", payload)

    results = await search("Tesla delivery numbers", limit=5)
    match = next((r for r in results if r.get("ticker") == "TSLA" and r.get("score") == 0.9), None)
    assert match is not None
    assert match["sentiment"] == "bullish"


# ── upsert_batch ───────────────────────────────────────────────────────────────

async def test_upsert_batch_stores_multiple_documents():
    docs = [
        (_uid(), "Fed raises interest rates by 25bps", {"ticker": "TLT", "tag": "macro"}),
        (_uid(), "Oil prices surge on OPEC output cut", {"ticker": "XLE", "tag": "macro"}),
        (_uid(), "Bitcoin breaks $100k", {"ticker": "BTC", "tag": "crypto"}),
    ]
    await upsert_batch(docs)

    results = await search("OPEC oil production decision", limit=5)
    tags = [r.get("tag") for r in results]
    assert "macro" in tags


async def test_upsert_batch_single_item():
    """upsert_batch should work with a list of exactly one document."""
    docs = [(_uid(), "Single document batch test", {"ticker": "TEST", "tag": "single"})]
    await upsert_batch(docs)  # must not raise


# ── search ─────────────────────────────────────────────────────────────────────

async def test_search_returns_semantically_relevant_result():
    """The most relevant document should rank first."""
    earnings_id = _uid()
    weather_id = _uid()

    await upsert_batch([
        (earnings_id, "Microsoft Azure cloud revenue surges 30% in quarterly earnings", {"topic": "earnings"}),
        (weather_id, "Heavy snowfall disrupts travel across the northeast", {"topic": "weather"}),
    ])

    results = await search("cloud computing revenue growth", limit=2)
    assert results[0]["topic"] == "earnings"


async def test_search_respects_limit():
    docs = [(_uid(), f"Article number {i} about stocks", {"i": i}) for i in range(5)]
    await upsert_batch(docs)

    results = await search("article about stocks", limit=3)
    assert len(results) <= 3


async def test_search_result_has_score():
    doc_id = _uid()
    await upsert(doc_id, "Semiconductor shortage impacts car manufacturers", {"ticker": "F"})

    results = await search("chip supply chain", limit=3)
    assert all("score" in r for r in results)
    assert all(0.0 <= r["score"] <= 1.0 for r in results)
