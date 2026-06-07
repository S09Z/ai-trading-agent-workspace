"""MemoryAgent — evaluates past signal outcomes and embeds them into Qdrant.

Run daily. For each unevaluated signal older than 1 day:
  1. Fetch closing prices at signal date + 1d/5d/30d via yfinance.
  2. Compute outcome: correct | incorrect | neutral.
  3. Store SignalOutcome row.
  4. Embed outcome text into Qdrant (type=signal_outcome) for future RAG retrieval.
"""

import asyncio
from datetime import UTC, date, datetime, timedelta

import yfinance as yf
from sqlalchemy import select

from agents.base import BaseAgent
from memory.database import AsyncSessionLocal, Signal, SignalOutcome
from memory.vector_store import upsert

# Minimum price move (%) to call a directional signal correct/incorrect
_THRESHOLD = 0.01  # 1%


def _label(signal_type: str, change_pct: float) -> str:
    """Return correct | incorrect | neutral for a given signal and price change."""
    if signal_type == "bullish":
        if change_pct > _THRESHOLD:
            return "correct"
        if change_pct < -_THRESHOLD:
            return "incorrect"
    elif signal_type == "bearish":
        if change_pct < -_THRESHOLD:
            return "correct"
        if change_pct > _THRESHOLD:
            return "incorrect"
    return "neutral"


def _fetch_close(ticker: str, on_date: date) -> float | None:
    """Return closing price on or just after on_date (skips weekends/holidays)."""
    try:
        df = yf.download(
            ticker,
            start=on_date,
            end=on_date + timedelta(days=7),
            progress=False,
            auto_adjust=True,
        )
        if df.empty:
            return None
        close = df["Close"].iloc[0]
        # yfinance may return a Series for multi-ticker; extract scalar
        return float(close.iloc[0]) if hasattr(close, "iloc") else float(close)
    except Exception:
        return None


class MemoryAgent(BaseAgent):
    name = "memory_agent"

    async def run(self) -> None:
        cutoff = datetime.now(UTC) - timedelta(days=1)

        # Find signals that have no outcome yet
        async with AsyncSessionLocal() as session:
            evaluated_ids = (
                await session.execute(select(SignalOutcome.signal_id))
            ).scalars().all()

            signals = (
                await session.execute(
                    select(Signal)
                    .where(
                        Signal.created_at < cutoff,
                        Signal.ticker != "MARKET",
                        Signal.signal_type.in_(["bullish", "bearish"]),
                        Signal.id.not_in(evaluated_ids) if evaluated_ids else Signal.id.isnot(None),
                    )
                    .limit(50)
                )
            ).scalars().all()

        if not signals:
            await self.log("evaluate", "No unevaluated signals found")
            return

        evaluated = 0
        embedded = 0

        for signal in signals:
            signal_date = signal.created_at.date()
            price_0 = await asyncio.to_thread(_fetch_close, signal.ticker, signal_date)
            price_1d = await asyncio.to_thread(
                _fetch_close, signal.ticker, signal_date + timedelta(days=1)
            )
            price_5d = await asyncio.to_thread(
                _fetch_close, signal.ticker, signal_date + timedelta(days=5)
            )
            price_30d = await asyncio.to_thread(
                _fetch_close, signal.ticker, signal_date + timedelta(days=30)
            )

            def _pct(p: float | None) -> float | None:
                if price_0 and p:
                    return (p - price_0) / price_0
                return None

            chg_1d = _pct(price_1d)
            chg_5d = _pct(price_5d)
            chg_30d = _pct(price_30d)

            outcome_5d = _label(signal.signal_type, chg_5d) if chg_5d is not None else None

            outcome = SignalOutcome(
                signal_id=signal.id,
                ticker=signal.ticker,
                signal_type=signal.signal_type,
                source_agent=signal.source_agent,
                price_at_signal=price_0,
                price_1d=price_1d,
                price_5d=price_5d,
                price_30d=price_30d,
                outcome_1d=_label(signal.signal_type, chg_1d) if chg_1d is not None else None,
                outcome_5d=outcome_5d,
                outcome_30d=_label(signal.signal_type, chg_30d) if chg_30d is not None else None,
                evaluated_at=datetime.now(UTC),
            )

            async with AsyncSessionLocal() as session:
                session.add(outcome)
                await session.commit()
                await session.refresh(outcome)

            evaluated += 1

            # Embed into Qdrant only if we have a 5d outcome to learn from
            if outcome_5d and price_0 and chg_5d is not None:
                chg_pct_str = f"{chg_5d * 100:+.1f}%"
                summary = (
                    f"A {signal.signal_type.upper()} signal on {signal.ticker} "
                    f"from {signal.source_agent} on {signal_date} was {outcome_5d.upper()}: "
                    f"price moved {chg_pct_str} in 5 days."
                )
                if signal.rationale:
                    summary += f" Original rationale: {signal.rationale[:120]}"

                await upsert(
                    doc_id=f"outcome_{outcome.id}",
                    text=summary,
                    payload={
                        "type": "signal_outcome",
                        "ticker": signal.ticker,
                        "signal_type": signal.signal_type,
                        "source_agent": signal.source_agent,
                        "outcome": outcome_5d,
                        "change_pct_5d": round(chg_5d * 100, 2),
                        "signal_date": str(signal_date),
                        "title": (
                            f"Past {signal.signal_type.upper()} signal on {signal.ticker} "
                            f"— outcome: {outcome_5d.upper()} ({chg_pct_str})"
                        ),
                        "outcome_summary": summary,
                    },
                )
                # Mark as embedded
                async with AsyncSessionLocal() as session:
                    row = await session.get(SignalOutcome, outcome.id)
                    if row:
                        row.embedded = True
                        await session.commit()
                embedded += 1

        await self.log(
            "evaluate",
            f"Evaluated {evaluated} signals, embedded {embedded} outcomes",
            meta={"evaluated": evaluated, "embedded": embedded},
        )
