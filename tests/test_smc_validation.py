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
