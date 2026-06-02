import asyncio
from functools import lru_cache

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from config.settings import get_settings

_settings = get_settings()
_client = AsyncQdrantClient(host=_settings.qdrant_host, port=_settings.qdrant_port)


@lru_cache(maxsize=1)
def _encoder():
    """Load once per process — model download (~90MB) happens on first call."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(_settings.embedding_model)


def _embed(text: str) -> list[float]:
    return _encoder().encode(text, normalize_embeddings=True).tolist()


def _embed_batch(texts: list[str]) -> list[list[float]]:
    return _encoder().encode(texts, normalize_embeddings=True).tolist()


async def ensure_collection() -> None:
    """Create the Qdrant collection if it doesn't exist."""
    existing = await _client.get_collections()
    names = {c.name for c in existing.collections}
    if _settings.qdrant_collection not in names:
        await _client.create_collection(
            collection_name=_settings.qdrant_collection,
            vectors_config=VectorParams(
                size=_settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )


async def upsert(doc_id: str, text: str, payload: dict) -> None:
    """Embed text and store in Qdrant. doc_id deduplicates on re-insert."""
    vector = await asyncio.to_thread(_embed, text)
    await _client.upsert(
        collection_name=_settings.qdrant_collection,
        points=[PointStruct(id=doc_id, vector=vector, payload=payload)],
    )


async def upsert_batch(docs: list[tuple[str, str, dict]]) -> None:
    """Batch embed and store. docs = [(id, text, payload), ...].

    Encodes all texts in one forward pass — much faster than calling
    upsert() in a loop when ingesting many articles at once.
    """
    ids, texts, payloads = zip(*docs)
    vectors = await asyncio.to_thread(_embed_batch, list(texts))
    points = [
        PointStruct(id=doc_id, vector=vector, payload=payload)
        for doc_id, vector, payload in zip(ids, vectors, payloads)
    ]
    await _client.upsert(collection_name=_settings.qdrant_collection, points=points)


async def search(query: str, limit: int = 5) -> list[dict]:
    """Return top-k most relevant documents for a query string."""
    vector = await asyncio.to_thread(_embed, query)
    results = await _client.search(
        collection_name=_settings.qdrant_collection,
        query_vector=vector,
        limit=limit,
        with_payload=True,
    )
    return [{"score": r.score, **r.payload} for r in results]
