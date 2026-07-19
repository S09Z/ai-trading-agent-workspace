"""Per-ticker stock endpoints — price history (yfinance) + AlphaOps analysis."""

import asyncio
import time

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cockpit.routers.outcomes import _to_schema as _outcome_to_schema
from cockpit.schemas import (
    StockAnalysisOut,
    StockBar,
    StockHistoryOut,
    StockMeta,
)
from memory.database import Signal, SignalOutcome, get_session

router = APIRouter()

# Module-level TTL cache keyed by ticker — matches the "delayed 15m" badge and
# avoids hammering yfinance on every page load / timeframe switch.
_HISTORY_TTL = 15 * 60  # seconds
_history_cache: dict[str, tuple[float, StockHistoryOut]] = {}


def _fetch_history(ticker: str) -> StockHistoryOut:
    """Synchronous — call via asyncio.to_thread.

    Fetches ~5Y of daily OHLCV once (the client slices by timeframe) plus a few
    fundamentals for the hero. Returns empty bars + a bare meta on any failure so
    the endpoint never raises to the client.
    """
    import yfinance as yf

    meta = StockMeta(ticker=ticker)
    try:
        df = yf.download(
            ticker, period="5y", interval="1d", progress=False, auto_adjust=True
        )
    except Exception:
        df = None

    bars: list[StockBar] = []
    if df is not None and not df.empty:
        # yfinance may return a single-level or (field, ticker) multiindex.
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        for idx, row in df.iterrows():
            bars.append(
                StockBar(
                    t=idx.strftime("%Y-%m-%d"),
                    o=float(row["Open"]),
                    h=float(row["High"]),
                    l=float(row["Low"]),
                    c=float(row["Close"]),
                    v=float(row["Volume"]),
                )
            )

    if bars:
        last = bars[-1]
        prev_close = bars[-2].c if len(bars) > 1 else last.c
        meta.price = last.c
        meta.change = round(last.c - prev_close, 4)
        meta.change_pct = (
            round((last.c - prev_close) / prev_close * 100, 2) if prev_close else None
        )
        meta.volume = last.v

    try:
        info = yf.Ticker(ticker).info or {}
        meta.name = info.get("longName") or info.get("shortName")
        meta.market_cap = info.get("marketCap")
        meta.pe = info.get("trailingPE")
    except Exception:
        pass

    return StockHistoryOut(meta=meta, bars=bars)


@router.get("/{ticker}/history", response_model=StockHistoryOut)
async def stock_history(ticker: str) -> StockHistoryOut:
    """~5Y daily OHLCV + hero meta for one ticker (15-min TTL cache)."""
    key = ticker.upper()
    cached = _history_cache.get(key)
    now = time.monotonic()
    if cached and now - cached[0] < _HISTORY_TTL:
        return cached[1]

    result = await asyncio.to_thread(_fetch_history, key)
    _history_cache[key] = (now, result)
    return result


@router.get("/{ticker}/analysis", response_model=StockAnalysisOut)
async def stock_analysis(
    ticker: str,
    session: AsyncSession = Depends(get_session),
) -> StockAnalysisOut:
    """Latest AlphaOps signal for the ticker + outcome accuracy.

    Prefers the FinancialAnalyst signal (composite score); falls back to the
    newest signal from any agent. Empty ``has_analysis`` state when none exists.
    """
    key = ticker.upper()

    signal = (
        await session.execute(
            select(Signal)
            .where(
                Signal.ticker == key,
                Signal.source_agent == "financial_analyst",
            )
            .order_by(Signal.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if signal is None:
        signal = (
            await session.execute(
                select(Signal)
                .where(Signal.ticker == key)
                .order_by(Signal.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    outcome_rows = (
        await session.execute(
            select(SignalOutcome)
            .where(SignalOutcome.ticker == key)
            .order_by(SignalOutcome.created_at.desc())
            .limit(20)
        )
    ).scalars().all()
    outcomes = [_outcome_to_schema(r) for r in outcome_rows]

    correct = sum(1 for r in outcome_rows if r.outcome_5d == "correct")
    incorrect = sum(1 for r in outcome_rows if r.outcome_5d == "incorrect")
    directional = correct + incorrect
    accuracy_pct = round(correct / directional * 100, 1) if directional else None

    if signal is None:
        return StockAnalysisOut(
            ticker=key,
            has_analysis=False,
            outcomes=outcomes,
            accuracy_pct=accuracy_pct,
        )

    return StockAnalysisOut(
        ticker=key,
        has_analysis=True,
        composite_score=signal.composite_score,
        composite_breakdown=signal.composite_breakdown or {},
        signal_type=signal.signal_type,
        confidence=signal.confidence,
        grade_short=signal.grade_short,
        grade_mid=signal.grade_mid,
        grade_long=signal.grade_long,
        rationale=signal.rationale,
        source_agent=signal.source_agent,
        created_at=signal.created_at,
        outcomes=outcomes,
        accuracy_pct=accuracy_pct,
    )
