from config.settings import get_settings
from memory.database import SMCEdgeStat


def test_smc_settings_defaults():
    s = get_settings()
    assert s.smc_interval == "1d"
    assert s.smc_period == "6mo"
    assert s.smc_horizon_days == 5
    assert s.smc_min_events == 30
    assert s.smc_swing_lookback == 5
    assert s.smc_impulse_atr_mult == 1.5


def test_smc_edge_stat_columns():
    cols = {c.name for c in SMCEdgeStat.__table__.columns}
    assert {"pattern", "bias", "interval", "sample_size",
            "mean_fwd_return", "hit_rate", "computed_at"} <= cols


import pandas as pd

from backtesting.smc_validation import aggregate, forward_return


def test_forward_return_basic():
    close = pd.Series([100.0, 101.0, 102.0, 104.0, 108.0, 110.0])
    assert forward_return(close, bar_index=0, horizon=5) == (110.0 / 100.0 - 1)


def test_forward_return_out_of_range_is_none():
    close = pd.Series([100.0, 101.0, 102.0])
    assert forward_return(close, bar_index=1, horizon=5) is None


def test_aggregate_computes_mean_and_hitrate():
    edges = [0.02, -0.01, 0.03, 0.04]        # already bias-sign-adjusted
    stat = aggregate(edges, min_events=3)
    assert stat["sample_size"] == 4
    assert stat["mean_fwd_return"] == round(sum(edges) / 4, 6)
    assert stat["hit_rate"] == 0.75          # 3 of 4 positive


def test_aggregate_below_min_events_returns_none():
    assert aggregate([0.02, 0.03], min_events=3) is None


from datetime import UTC, datetime, timedelta

from backtesting.smc_validation import event_study


def _series_df(closes: list[float]) -> pd.DataFrame:
    idx = [datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=i) for i in range(len(closes))]
    return pd.DataFrame(
        {"Open": closes, "High": [c + 0.01 for c in closes],
         "Low": [c - 0.01 for c in closes], "Close": closes,
         "Volume": [1_000] * len(closes)},
        index=pd.DatetimeIndex(idx),
    )


def test_event_study_aggregates_by_pattern_bias():
    # Craft a bullish FVG then a rising series so its forward return is positive.
    closes = [10.0, 11.8, 12.2] + [12.2 + 0.5 * i for i in range(1, 8)]
    df = _series_df(closes)
    # force a bullish FVG on bar 2 by widening the low/high gap
    df.loc[df.index[0], "High"] = 10.5
    df.loc[df.index[2], "Low"] = 10.8
    stats = event_study(
        {"TEST": df}, interval="1d", horizon=3, min_events=1,
        impulse_atr_mult=1.5, swing_lookback=5,
    )
    fvg = [s for s in stats if s["pattern"] == "fvg" and s["bias"] == "bullish"]
    assert fvg and fvg[0]["sample_size"] >= 1
    assert fvg[0]["mean_fwd_return"] > 0        # bullish FVG preceded a rise
    assert fvg[0]["interval"] == "1d"


# ── Task 1 tests: get_smc_context ─────────────────────────────────────────────
from unittest.mock import AsyncMock, patch

from agents.smc import SMCDetection, get_smc_context


async def test_get_smc_context_empty_when_no_candles():
    with patch("collectors.market_data._fetch_ohlcv", return_value=[]):
        result = await get_smc_context("AAPL")
    assert result == ""


async def test_get_smc_context_empty_when_no_detections():
    from datetime import UTC, datetime
    candles = [
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0,
         "volume": 1000.0, "timestamp": datetime(2026, 1, i + 1, tzinfo=UTC)}
        for i in range(5)
    ]
    with patch("collectors.market_data._fetch_ohlcv", return_value=candles), \
         patch("agents.smc.detect_all", return_value=[]):
        result = await get_smc_context("AAPL")
    assert result == ""


async def test_get_smc_context_formats_detection_without_edge_stats(db_session):
    from datetime import UTC, datetime
    candles = [
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0,
         "volume": 1000.0, "timestamp": datetime(2026, 1, i + 1, tzinfo=UTC)}
        for i in range(5)
    ]
    detection = SMCDetection(
        pattern="fvg", bias="bullish", bar_index=4,
        timestamp=datetime(2026, 1, 5, tzinfo=UTC),
        zone_low=99.0, zone_high=101.0, strength=0.02,
    )
    with patch("collectors.market_data._fetch_ohlcv", return_value=candles), \
         patch("agents.smc.detect_all", return_value=[detection]):
        result = await get_smc_context("AAPL")
    assert "SMC Detections:" in result
    assert "Bullish FVG" in result
    assert "2026-01-05" in result


async def test_get_smc_context_annotates_with_edge_stats(db_session, db_engine):
    from datetime import UTC, datetime
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from memory.database import SMCEdgeStat

    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        s.add(SMCEdgeStat(
            pattern="fvg", bias="bullish", interval="1d",
            sample_size=142, mean_fwd_return=0.006, hit_rate=0.57,
        ))
        await s.commit()

    candles = [
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0,
         "volume": 1000.0, "timestamp": datetime(2026, 1, i + 1, tzinfo=UTC)}
        for i in range(5)
    ]
    detection = SMCDetection(
        pattern="fvg", bias="bullish", bar_index=4,
        timestamp=datetime(2026, 1, 5, tzinfo=UTC),
        zone_low=99.0, zone_high=101.0, strength=0.02,
    )
    with patch("collectors.market_data._fetch_ohlcv", return_value=candles), \
         patch("agents.smc.detect_all", return_value=[detection]):
        result = await get_smc_context("AAPL")
    assert "n=142" in result
    assert "57%" in result
    assert "+0.6%" in result
