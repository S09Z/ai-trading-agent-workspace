import asyncio

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from agents.base import BaseAgent
from agents.smc import detect_all
from collectors.market_data import fetch_ohlcv, fetch_watchlist_snapshots
from config.settings import get_settings
from memory.database import AsyncSessionLocal, MarketSnapshot, SMCEdgeStat

SPIKE_THRESHOLD = 3.0  # percent change that counts as a significant move


async def _check_ticker_smc(ticker: str, edge: dict, s) -> list[dict]:
    candles = await fetch_ohlcv(ticker, period=s.smc_period, interval=s.smc_interval)
    if not candles:
        return []

    df = pd.DataFrame(
        {
            "Open": [c["open"] for c in candles],
            "High": [c["high"] for c in candles],
            "Low": [c["low"] for c in candles],
            "Close": [c["close"] for c in candles],
            "Volume": [c["volume"] for c in candles],
        },
        index=pd.DatetimeIndex([c["timestamp"] for c in candles]),
    )

    detections = detect_all(df, impulse_atr_mult=s.smc_impulse_atr_mult, swing_lookback=s.smc_swing_lookback)
    fresh = [d for d in detections if d.bar_index >= len(df) - s.smc_fresh_bars]

    return [
        {
            "ticker": ticker,
            "pattern": d.pattern,
            "bias": d.bias,
            "hist_hit_rate": edge[(d.pattern, d.bias)].hit_rate if (d.pattern, d.bias) in edge else None,
        }
        for d in fresh
    ]


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

        # Load SMC edge stats and check for fresh SMC patterns
        s = get_settings()
        async with AsyncSessionLocal() as session:
            rows = (await session.execute(select(SMCEdgeStat))).scalars().all()
        edge = {(r.pattern, r.bias): r for r in rows}

        results = await asyncio.gather(*[_check_ticker_smc(t, edge, s) for t in s.watchlist])
        for events in results:
            for ev in events:
                await self.log(
                    "smc_detected",
                    f"{ev['ticker']} {ev['bias']} {ev['pattern']} detected",
                    meta=ev,
                )

        await self.log(
            "poll",
            f"Stored {stored} snapshots, {len(spikes)} spike(s) detected",
        )
