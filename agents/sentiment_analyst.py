from sqlalchemy import select

from agents.base import BaseAgent
from intelligence.sentiment import analyze_sentiment
from memory.database import Article, AsyncSessionLocal, Signal

SIGNAL_THRESHOLD = 0.65  # abs(score) must exceed this to create a Signal
BATCH_SIZE = 20


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
                    for ticker in (art.tickers or []):
                        session.add(Signal(
                            ticker=ticker,
                            signal_type=signal_type,
                            confidence=round(abs(result["score"]), 4),
                            source_agent=self.name,
                            rationale=art.title[:200],
                        ))
                    await session.commit()
                    signals_created += len(art.tickers or [])

        await self.log(
            "analyze",
            f"Analyzed {analyzed} articles, created {signals_created} signal(s)",
        )
