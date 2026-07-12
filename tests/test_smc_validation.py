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
