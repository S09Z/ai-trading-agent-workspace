from sqlalchemy.exc import IntegrityError

from agents.base import BaseAgent
from collectors.news import fetch_all
from memory.database import Article, AsyncSessionLocal
from memory.vector_store import ensure_collection, upsert


class NewsHunterAgent(BaseAgent):
    name = "news_hunter"

    async def run(self) -> None:
        await ensure_collection()
        articles = await fetch_all()
        new_count = 0

        for data in articles:
            async with AsyncSessionLocal() as session:
                try:
                    article = Article(**data)
                    session.add(article)
                    await session.commit()
                    await session.refresh(article)

                    embed_text = f"{article.title} {article.content or ''}".strip()
                    await upsert(
                        article.id,
                        embed_text,
                        {
                            "title": article.title,
                            "source": article.source,
                            "url": article.url,
                            "tickers": article.tickers,
                        },
                    )

                    article.embedded = True
                    await session.commit()
                    new_count += 1

                except IntegrityError:
                    await session.rollback()  # duplicate URL — skip silently

        await self.log("fetch", f"Stored {new_count} new articles from {len(articles)} fetched")
