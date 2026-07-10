from datetime import UTC, datetime, timedelta

import pandas as pd

from agents.smc import SMCDetection, detect_fvg


def _mk_df(rows: list[dict]) -> pd.DataFrame:
    idx = [datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=i) for i in range(len(rows))]
    return pd.DataFrame(rows, index=pd.DatetimeIndex(idx))


def test_bullish_fvg_detected():
    # bar2.low (10.8) > bar0.high (10.5) → bullish gap on bar index 2
    df = _mk_df([
        {"Open": 10.0, "High": 10.5, "Low": 9.5,  "Close": 10.0, "Volume": 1_000},
        {"Open": 10.5, "High": 12.0, "Low": 10.4, "Close": 11.8, "Volume": 2_000},
        {"Open": 11.9, "High": 12.5, "Low": 10.8, "Close": 12.2, "Volume": 1_500},
    ])
    dets = detect_fvg(df)
    assert len(dets) == 1
    d = dets[0]
    assert isinstance(d, SMCDetection)
    assert d.pattern == "fvg" and d.bias == "bullish" and d.bar_index == 2
    assert d.zone_low == 10.5 and d.zone_high == 10.8


def test_bearish_fvg_detected():
    # bar2.high (9.8) < bar0.low (10.5) → bearish gap on bar index 2
    df = _mk_df([
        {"Open": 11.0, "High": 11.5, "Low": 10.5, "Close": 11.0, "Volume": 1_000},
        {"Open": 10.4, "High": 10.5, "Low": 8.5,  "Close": 8.7,  "Volume": 2_000},
        {"Open": 8.6,  "High": 9.8,  "Low": 8.0,  "Close": 9.2,  "Volume": 1_500},
    ])
    dets = detect_fvg(df)
    assert len(dets) == 1
    assert dets[0].bias == "bearish" and dets[0].zone_low == 9.8 and dets[0].zone_high == 10.5


def test_no_fvg_when_no_gap():
    df = _mk_df([
        {"Open": 10.0, "High": 10.5, "Low": 9.5, "Close": 10.0, "Volume": 1_000},
        {"Open": 10.1, "High": 10.6, "Low": 9.6, "Close": 10.2, "Volume": 1_000},
        {"Open": 10.2, "High": 10.7, "Low": 9.7, "Close": 10.3, "Volume": 1_000},
    ])
    assert detect_fvg(df) == []
