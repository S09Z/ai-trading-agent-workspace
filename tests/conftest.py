import os

# Must be set before any project module is imported so get_settings()
# picks up the test collection name on its first call.
os.environ.setdefault("QDRANT_COLLECTION", "alphaops_test")

from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import get_settings  # noqa: E402

# Clear the lru_cache so our env-var overrides above take effect.
get_settings.cache_clear()

from memory.database import Base  # noqa: E402

# ── Shared settings ────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def settings():
    return get_settings()


# ── Database ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def db_engine(settings):
    """Create all tables once for the whole test session."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(text(
                "SELECT create_hypertable('market_snapshots', 'timestamp', if_not_exists => TRUE)"
            ))
        except Exception:
            pass  # plain PostgreSQL without TimescaleDB
        # Phase 7 migration — grade columns
        for col in ("grade_short", "grade_mid", "grade_long"):
            await conn.execute(text(
                f"ALTER TABLE signals ADD COLUMN IF NOT EXISTS {col} VARCHAR(1)"
            ))
        # Phase 8 migration — composite score columns
        await conn.execute(text(
            "ALTER TABLE signals ADD COLUMN IF NOT EXISTS composite_score DOUBLE PRECISION"
        ))
        await conn.execute(text(
            "ALTER TABLE signals ADD COLUMN IF NOT EXISTS composite_breakdown JSON"
        ))
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    """Per-test session. All rows are deleted from every table after each test."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    # Cleanup: delete rows in reverse dependency order
    async with db_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# ── Qdrant ─────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def qdrant_test_collection(settings):
    """Ensure a clean test collection exists for the session; tear it down after."""
    from memory.vector_store import _client, ensure_collection

    try:
        await _client.delete_collection(settings.qdrant_collection)
    except Exception:
        pass

    await ensure_collection()
    yield
    try:
        await _client.delete_collection(settings.qdrant_collection)
    except Exception:
        pass


# ── Claude ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_claude():
    """Patch the Anthropic client so no real API calls are made in tests."""
    response = MagicMock()
    response.content = [MagicMock(text="OK")]
    with patch("intelligence.claude_client._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=response)
        yield mock_client
