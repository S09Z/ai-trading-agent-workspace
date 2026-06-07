from sqlalchemy import select

from agents.base import BaseAgent
from intelligence.sentiment import analyze_sentiment
from memory.database import Article, AsyncSessionLocal, Signal

SIGNAL_THRESHOLD = 0.65  # abs(score) must exceed this to create a Signal
BATCH_SIZE = 20


def _grades(signal_type: str, confidence: float) -> tuple[str, str, str]:
    """Return (grade_short, grade_mid, grade_long) for a sentiment signal.

    Short-term sentiment impact is strongest; it decays for mid/long horizons.
    S=Strong Buy, A=Buy, B=Hold, C=Sell.
    """
    if signal_type == "bearish":
        short = "C" if confidence >= 0.80 else "C"
        mid   = "C" if confidence >= 0.80 else "B"
        long  = "B"
        return short, mid, long
    if signal_type == "bullish":
        if confidence >= 0.80:
            return "S", "A", "B"
        return "A", "B", "B"
    return "B", "B", "B"  # alert / watchlist


class SentimentAnalystAgent(BaseAgent):
    name = "sentiment_analyst"

    async def run(self) -> None:
        async with AsyncSessionLocal() as session:
            rows = (
                await session.execute(
                    select(Article)
                    .where(Article.sentiment.is_(None))
                    .limit(BATCH_SIZE)
                )
            ).scalars().all()

        analyzed = 0
        signals_created = 0

        for article in rows:
            result = await analyze_sentiment(article.title, article.content or "")

            async with AsyncSessionLocal() as session:
                art = await session.get(Article, article.id)
                if art is None:
                    continue
                art.sentiment = result["sentiment"]
                art.sentiment_score = result["score"]
                await session.commit()
                analyzed += 1

                if abs(result["score"]) >= SIGNAL_THRESHOLD:
                    signal_type = "bullish" if result["score"] > 0 else "bearish"
                    conf = round(abs(result["score"]), 4)
                    gs, gm, gl = _grades(signal_type, conf)
                    for ticker in (art.tickers or []):
                        session.add(Signal(
                            ticker=ticker,
                            signal_type=signal_type,
                            confidence=conf,
                            source_agent=self.name,
                            rationale=art.title[:200],
                            grade_short=gs,
                            grade_mid=gm,
                            grade_long=gl,
                        ))
                    await session.commit()
                    signals_created += len(art.tickers or [])

        await self.log(
            "analyze",
            f"Analyzed {analyzed} articles, created {signals_created} signal(s)",
        )
