import asyncio
from datetime import UTC, datetime

import yfinance as yf

from config.settings import get_settings

_settings = get_settings()


def _fetch_snapshot(ticker: str) -> dict | None:
    """Fetch the latest daily OHLCV candle + change-from-prev-close for one ticker."""
    try:
        hist = yf.Ticker(ticker).history(period="2d", interval="1d")
        if hist.empty:
            return None
        last = hist.iloc[-1]
        prev_close = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else float(last["Open"])
        price = float(last["Close"])
        return {
            "ticker": ticker,
            "timestamp": datetime.now(UTC).replace(second=0, microsecond=0),
            "open": float(last["Open"]),
            "high": float(last["High"]),
            "low": float(last["Low"]),
            "close": price,
            "volume": float(last["Volume"]),
            "change_pct": (price - prev_close) / prev_close * 100 if prev_close else 0.0,
        }
    except Exception:
        return None


def _fetch_ohlcv(ticker: str, period: str = "1d", interval: str = "1m") -> list[dict]:
    """Fetch a series of OHLCV candles for one ticker."""
    try:
        hist = yf.Ticker(ticker).history(period=period, interval=interval)
        if hist.empty:
            return []
        candles = []
        for ts, row in hist.iterrows():
            dt = ts.to_pydatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            candles.append({
                "ticker": ticker,
                "timestamp": dt,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
            })
        return candles
    except Exception:
        return []


async def fetch_snapshot(ticker: str) -> dict | None:
    """Async wrapper for a single ticker snapshot."""
    return await asyncio.to_thread(_fetch_snapshot, ticker)


async def fetch_ohlcv(ticker: str, period: str = "1d", interval: str = "1m") -> list[dict]:
    """Async wrapper for a series of OHLCV candles."""
    return await asyncio.to_thread(_fetch_ohlcv, ticker, period, interval)


async def fetch_watchlist_snapshots() -> list[dict]:
    """Fetch current snapshots for all watchlist tickers concurrently."""
    results = await asyncio.gather(
        *[fetch_snapshot(t) for t in _settings.watchlist],
        return_exceptions=True,
    )
    return [r for r in results if isinstance(r, dict)]
