"""Tests for the market data collector — yfinance OHLCV fetching.

yfinance calls are mocked — no real network requests.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


def _make_hist(rows: list[tuple]) -> pd.DataFrame:
    """Build a mock yfinance history DataFrame from (o, h, l, c, v) tuples."""
    dates = pd.date_range("2024-01-14", periods=len(rows), freq="D", tz=UTC)
    return pd.DataFrame(
        [{"Open": o, "High": h, "Low": lo, "Close": c, "Volume": v} for o, h, lo, c, v in rows],
        index=dates,
    )


@pytest.fixture
def mock_ticker_factory():
    """Returns a factory that creates a mock yf.Ticker with the given history."""
    def _factory(rows):
        mock = MagicMock()
        mock.history.return_value = _make_hist(rows)
        return mock
    return _factory


# ── fetch_snapshot ─────────────────────────────────────────────────────────────

async def test_fetch_snapshot_returns_normalised_dict(mock_ticker_factory):
    from collectors.market_data import fetch_snapshot

    rows = [(180.0, 185.0, 179.0, 181.0, 50_000_000), (183.0, 188.0, 182.0, 186.0, 55_000_000)]
    with patch("collectors.market_data.yf.Ticker", return_value=mock_ticker_factory(rows)):
        result = await fetch_snapshot("AAPL")

    assert result is not None
    assert result["ticker"] == "AAPL"
    assert result["close"] == pytest.approx(186.0)
    assert result["open"] == pytest.approx(183.0)
    assert result["volume"] == pytest.approx(55_000_000)
    assert "change_pct" in result
    assert isinstance(result["timestamp"], datetime)
    assert result["timestamp"].tzinfo is not None


async def test_fetch_snapshot_calculates_change_pct(mock_ticker_factory):
    from collectors.market_data import fetch_snapshot

    # prev_close=100, close=105 → +5%
    rows = [(100.0, 102.0, 99.0, 100.0, 1_000_000), (104.0, 106.0, 103.0, 105.0, 1_200_000)]
    with patch("collectors.market_data.yf.Ticker", return_value=mock_ticker_factory(rows)):
        result = await fetch_snapshot("SPY")

    assert result["change_pct"] == pytest.approx(5.0)


async def test_fetch_snapshot_returns_none_on_empty_history(mock_ticker_factory):
    from collectors.market_data import fetch_snapshot

    mock = MagicMock()
    mock.history.return_value = pd.DataFrame()
    with patch("collectors.market_data.yf.Ticker", return_value=mock):
        result = await fetch_snapshot("FAKE")

    assert result is None


async def test_fetch_snapshot_returns_none_on_exception():
    from collectors.market_data import fetch_snapshot

    mock = MagicMock()
    mock.history.side_effect = Exception("network error")
    with patch("collectors.market_data.yf.Ticker", return_value=mock):
        result = await fetch_snapshot("ERR")

    assert result is None


# ── fetch_ohlcv ────────────────────────────────────────────────────────────────

async def test_fetch_ohlcv_returns_candle_list(mock_ticker_factory):
    from collectors.market_data import fetch_ohlcv

    rows = [(180.0, 185.0, 179.0, 181.0, 50_000_000), (183.0, 188.0, 182.0, 186.0, 55_000_000)]
    with patch("collectors.market_data.yf.Ticker", return_value=mock_ticker_factory(rows)):
        candles = await fetch_ohlcv("NVDA")

    assert len(candles) == 2
    assert candles[0]["ticker"] == "NVDA"
    assert candles[0]["close"] == pytest.approx(181.0)
    assert candles[1]["close"] == pytest.approx(186.0)


async def test_fetch_ohlcv_returns_empty_on_error():
    from collectors.market_data import fetch_ohlcv

    mock = MagicMock()
    mock.history.side_effect = Exception("timeout")
    with patch("collectors.market_data.yf.Ticker", return_value=mock):
        candles = await fetch_ohlcv("ERR")

    assert candles == []


# ── fetch_watchlist_snapshots ──────────────────────────────────────────────────

async def test_fetch_watchlist_snapshots_returns_results():
    from collectors.market_data import fetch_watchlist_snapshots

    snap = {
        "ticker": "AAPL", "timestamp": datetime.now(UTC),
        "open": 180.0, "high": 185.0, "low": 179.0, "close": 182.0,
        "volume": 50_000_000.0, "change_pct": 1.2,
    }
    with patch("collectors.market_data.fetch_snapshot", return_value=snap):
        results = await fetch_watchlist_snapshots()

    assert len(results) > 0
    assert all(r["close"] == pytest.approx(182.0) for r in results)


async def test_fetch_watchlist_snapshots_skips_none_results():
    from collectors.market_data import fetch_watchlist_snapshots

    with patch("collectors.market_data.fetch_snapshot", return_value=None):
        results = await fetch_watchlist_snapshots()

    assert results == []
