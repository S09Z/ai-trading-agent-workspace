import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text, text
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config.settings import get_settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Article(Base):
    """A news article collected from any source."""

    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)       # Claude-generated
    source: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(2000), unique=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    tickers: Mapped[list] = mapped_column(JSON, default=list)       # ["AAPL", "NVDA"]
    sentiment: Mapped[str | None] = mapped_column(String(20))       # bullish | bearish | neutral
    sentiment_score: Mapped[float | None] = mapped_column(Float)    # -1.0 to 1.0
    embedded: Mapped[bool] = mapped_column(Boolean, default=False)  # stored in Qdrant


class MarketSnapshot(Base):
    """OHLCV candle for a single ticker.

    Converted to a TimescaleDB hypertable on 'timestamp' by init_db(),
    enabling automatic time-based partitioning and fast range queries.
    """

    __tablename__ = "market_snapshots"

    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)


class Signal(Base):
    """A trading signal produced by any agent."""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    signal_type: Mapped[str] = mapped_column(String(20))        # bullish | bearish | alert | watchlist
    confidence: Mapped[float] = mapped_column(Float)            # 0.0 – 1.0
    source_agent: Mapped[str] = mapped_column(String(50))
    rationale: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class AgentLog(Base):
    """Append-only activity log for all agents — feeds the virtual office UI."""

    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String(50), index=True)
    action: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(10), default="info")  # info | warning | error
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


# ── Engine + session factory ───────────────────────────────────────────────────

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    echo=_settings.debug,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a scoped async session."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create all tables and enable TimescaleDB hypertable for market data.

    Safe to call on every startup — CREATE TABLE and create_hypertable are
    both idempotent when if_not_exists is set.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(text(
                "SELECT create_hypertable('market_snapshots', 'timestamp', if_not_exists => TRUE)"
            ))
        except Exception:
            # Running against plain PostgreSQL (no TimescaleDB) — fine for local dev
            pass
