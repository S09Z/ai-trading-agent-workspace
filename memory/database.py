import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool

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
    grade_short: Mapped[str | None] = mapped_column(String(1))  # S | A | B | C
    grade_mid: Mapped[str | None] = mapped_column(String(1))
    grade_long: Mapped[str | None] = mapped_column(String(1))
    composite_score: Mapped[float | None] = mapped_column(Float)  # 0–100 IC-weighted score
    composite_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)  # per-bucket scores
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class SignalOutcome(Base):
    """Price outcome for a past trading signal — feeds agent memory."""

    __tablename__ = "signal_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_id: Mapped[int] = mapped_column(Integer, ForeignKey("signals.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    signal_type: Mapped[str] = mapped_column(String(20))           # bullish | bearish | watchlist
    source_agent: Mapped[str] = mapped_column(String(50))
    price_at_signal: Mapped[float | None] = mapped_column(Float)
    price_1d: Mapped[float | None] = mapped_column(Float)
    price_5d: Mapped[float | None] = mapped_column(Float)
    price_30d: Mapped[float | None] = mapped_column(Float)
    outcome_1d: Mapped[str | None] = mapped_column(String(20))     # correct | incorrect | neutral
    outcome_5d: Mapped[str | None] = mapped_column(String(20))
    outcome_30d: Mapped[str | None] = mapped_column(String(20))
    embedded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FactorScore(Base):
    """IC/IR score for one alpha factor on one ticker — refreshed weekly."""

    __tablename__ = "factor_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(50))       # "ret_3m", "realized_vol_20d", ...
    bucket: Mapped[str] = mapped_column(String(20))     # momentum | value | quality | liquidity | volatility
    ic: Mapped[float] = mapped_column(Float)            # Spearman IC vs 5d forward return
    status: Mapped[str] = mapped_column(String(10))     # alive | reversed | dead
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


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
    poolclass=NullPool,
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
        # Phase 7 migration — add grade columns to existing signals table
        for col in ("grade_short", "grade_mid", "grade_long"):
            await conn.execute(text(
                f"ALTER TABLE signals ADD COLUMN IF NOT EXISTS {col} VARCHAR(1)"
            ))
        # Phase 8 migration — add composite score columns to existing signals table
        await conn.execute(text(
            "ALTER TABLE signals ADD COLUMN IF NOT EXISTS composite_score DOUBLE PRECISION"
        ))
        await conn.execute(text(
            "ALTER TABLE signals ADD COLUMN IF NOT EXISTS composite_breakdown JSON"
        ))
