from sqlalchemy.exc import IntegrityError

from agents.base import BaseAgent
from collectors.market_data import fetch_watchlist_snapshots
from memory.database import AsyncSessionLocal, MarketSnapshot

SPIKE_THRESHOLD = 3.0  # percent change that counts as a significant move


class MarketWatchAgent(BaseAgent):
    name = "market_watch"

    async def run(self) -> None:
        snapshots = await fetch_watchlist_snapshots()
        stored = 0

        for snap in snapshots:
            async with AsyncSessionLocal() as session:
                try:
                    session.add(MarketSnapshot(
                        ticker=snap["ticker"],
                        timestamp=snap["timestamp"],
                        open=snap["open"],
                        high=snap["high"],
                        low=snap["low"],
                        close=snap["close"],
                        volume=snap["volume"],
                    ))
                    await session.commit()
                    stored += 1
                except IntegrityError:
                    await session.rollback()  # same (ticker, timestamp) already stored

        # Log significant price moves
        spikes = [s for s in snapshots if abs(s.get("change_pct", 0)) >= SPIKE_THRESHOLD]
        for spike in spikes:
            pct = spike["change_pct"]
            sign = "+" if pct > 0 else ""
            await self.log(
                "spike_detected",
                f"{spike['ticker']} {sign}{pct:.1f}% move detected",
                level="warning",
                meta={k: spike[k] for k in ("ticker", "close", "change_pct")},
            )

        await self.log(
            "poll",
            f"Stored {stored} snapshots, {len(spikes)} spike(s) detected",
        )
