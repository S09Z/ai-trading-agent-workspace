"""DiscoveryAgent — surfaces tickers outside the watchlist with strong news mentions."""

import asyncio
import re
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from agents.base import BaseAgent
from config.settings import get_settings
from config.universe import UNIVERSE_TICKERS
from memory.database import Article, AsyncSessionLocal, Signal

_settings = get_settings()

_SYSTEM = (
    "You are a stock screening analyst identifying early-opportunity tickers."
    " Be brief and structured."
)

_DISCOVERY_HOURS = 24   # article look-back window
_TOP_N = 5              # max candidates per run
_MIN_MENTIONS = 2       # minimum article mentions to qualify
_RECENTLY_HOURS = 24    # skip ticker if already discovered within this window
_VALID_GRADES = {"S", "A", "B", "C"}

_UNIVERSE = frozenset(UNIVERSE_TICKERS)


def _count_mentions(articles: list) -> Counter:
    """Count universe ticker mentions across article titles + content."""
    counter: Counter = Counter()
    for art in articles:
        text = f"{art.title} {art.content or ''}"
        for ticker in _UNIVERSE:
            if re.search(rf"\b{re.escape(ticker)}\b", text, re.IGNORECASE):
                counter[ticker] += 1
    return counter


def _fetch_price(ticker_symbol: str) -> dict | None:
    """Synchronous yfinance snapshot — call via asyncio.to_thread."""
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker_symbol).history(period="2d", interval="1d")
        if hist.empty:
            return None
        last = hist.iloc[-1]
        prev = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else float(last["Open"])
        price = float(last["Close"])
        return {
            "price": price,
            "volume": float(last["Volume"]),
            "change_pct": (price - prev) / prev * 100 if prev else 0.0,
        }
    except Exception:
        return None


def _parse_response(text: str) -> tuple[str, float, str | None, str | None, str | None, str]:
    """Parse structured LLM response → (signal_type, confidence, gs, gm, gl, rationale)."""

    def _grade(label: str) -> str | None:
        m = re.search(rf"{label}[:\s]+([SABC])", text, re.IGNORECASE)
        return m.group(1).upper() if m and m.group(1).upper() in _VALID_GRADES else None

    sm = re.search(r"SIGNAL[:\s]+(bullish|bearish|watchlist)", text, re.IGNORECASE)
    signal_type = sm.group(1).lower() if sm else "watchlist"

    cm = re.search(r"CONFIDENCE[:\s]+(0\.\d+|1\.0+)", text)
    confidence = float(cm.group(1)) if cm else 0.5

    rm = re.search(r"RATIONALE[:\s]+(.+)", text, re.IGNORECASE | re.DOTALL)
    rationale = rm.group(1).strip()[:500] if rm else text[:500]

    return signal_type, confidence, _grade("SHORT"), _grade("MID"), _grade("LONG"), rationale


class DiscoveryAgent(BaseAgent):
    name = "discovery_agent"

    async def run(self) -> None:
        watchlist = frozenset(t.upper() for t in _settings.watchlist)
        cutoff = datetime.now(UTC) - timedelta(hours=_DISCOVERY_HOURS)

        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(
                    select(Article)
                    .where(Article.collected_at >= cutoff)
                    .order_by(Article.collected_at.desc())
                    .limit(200)
                )
            ).scalars().all()

        if not rows:
            await self.log("run", "No recent articles — nothing to discover")
            return

        counts = _count_mentions(rows)

        # Keep only tickers not in watchlist that meet the mention threshold
        candidates = [
            (ticker, count)
            for ticker, count in counts.most_common()
            if ticker not in watchlist and count >= _MIN_MENTIONS
        ][:_TOP_N]

        if not candidates:
            await self.log(
                "run",
                f"Scanned {len(rows)} articles — no candidates above min_mentions={_MIN_MENTIONS}",
            )
            return

        discovered = 0
        for ticker, mention_count in candidates:
            if await self._recently_discovered(ticker):
                continue

            snap = await asyncio.to_thread(_fetch_price, ticker)
            if snap is None:
                await self.log("skip", f"{ticker}: no price data available")
                continue

            pat = re.compile(rf"\b{re.escape(ticker)}\b", re.IGNORECASE)
            titles = [
                art.title for art in rows
                if pat.search(f"{art.title} {art.content or ''}")
            ][:5]
            context = "\n".join(f"- {t}" for t in titles)

            prompt = (
                f"Ticker: {ticker}\n"
                f"Mentioned in {mention_count} recent articles.\n"
                f"Recent headlines:\n{context}\n\n"
                f"Price: ${snap['price']:.2f}  "
                f"Change: {snap['change_pct']:+.1f}%  "
                f"Volume: {snap['volume']:,.0f}\n\n"
                "Assess if this ticker is a discovery opportunity worth watching.\n\n"
                "Respond EXACTLY in this format:\n"
                "SIGNAL: <bullish|bearish|watchlist>\n"
                "CONFIDENCE: <0.0-1.0>\n"
                "SHORT: <S|A|B|C>\n"
                "MID: <S|A|B|C>\n"
                "LONG: <S|A|B|C>\n"
                "RATIONALE: <1-2 sentence assessment>\n\n"
                "Grades: S=Strong Buy, A=Buy, B=Hold, C=Sell"
            )

            from intelligence.llm import analyze
            response = await analyze(prompt, system=_SYSTEM, max_tokens=200)

            signal_type, confidence, gs, gm, gl, rationale = _parse_response(response)

            async with AsyncSessionLocal() as session:
                session.add(Signal(
                    ticker=ticker,
                    signal_type=signal_type,
                    confidence=confidence,
                    source_agent=self.name,
                    rationale=rationale,
                    grade_short=gs,
                    grade_mid=gm,
                    grade_long=gl,
                    meta={"mention_count": mention_count, "change_pct": snap["change_pct"]},
                ))
                await session.commit()

            await self.log(
                "discover",
                f"{ticker}: {signal_type} (confidence={confidence:.2f}) "
                f"mentions={mention_count} change={snap['change_pct']:+.1f}%",
                meta={"ticker": ticker, "signal_type": signal_type, "mention_count": mention_count},
            )
            discovered += 1

        await self.log(
            "run",
            f"Discovery complete — {discovered} new ticker(s) from {len(rows)} articles",
        )

    async def _recently_discovered(self, ticker: str) -> bool:
        cutoff = datetime.now(UTC) - timedelta(hours=_RECENTLY_HOURS)
        async with AsyncSessionLocal() as session:
            row = (
                await session.execute(
                    select(Signal).where(
                        Signal.ticker == ticker,
                        Signal.source_agent == self.name,
                        Signal.created_at >= cutoff,
                    ).limit(1)
                )
            ).scalars().first()
        return row is not None
