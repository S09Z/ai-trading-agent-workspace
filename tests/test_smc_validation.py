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
