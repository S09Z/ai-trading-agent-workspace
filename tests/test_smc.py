from datetime import UTC, datetime, timedelta

import pandas as pd

from agents.smc import (
    SMCDetection,
    detect_all,
    detect_fvg,
    detect_liquidity_sweep,
    detect_order_block,
)


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


def _flat_rows(n: int, price: float = 10.0) -> list[dict]:
    # small-range candles so ATR14 is small and the impulse stands out
    return [{"Open": price, "High": price + 0.1, "Low": price - 0.1,
             "Close": price, "Volume": 1_000} for _ in range(n)]


def test_bullish_order_block_detected():
    rows = _flat_rows(15)                       # warm up ATR14
    # down candle (OB)
    rows.append({"Open": 10.0, "High": 10.05, "Low": 9.7, "Close": 9.75, "Volume": 1_000})
    # impulse up
    rows.append({"Open": 9.8, "High": 12.0, "Low": 9.8, "Close": 11.9, "Volume": 3_000})
    df = _mk_df(rows)
    dets = detect_order_block(df, impulse_atr_mult=1.5)
    assert len(dets) == 1
    d = dets[0]
    assert d.pattern == "order_block" and d.bias == "bullish"
    assert d.bar_index == 15                    # the down candle before the impulse
    assert d.zone_low == 9.7 and d.zone_high == 10.05


def test_no_order_block_without_impulse():
    df = _mk_df(_flat_rows(20))
    assert detect_order_block(df, impulse_atr_mult=1.5) == []


def test_bearish_order_block_detected():
    rows = _flat_rows(15)                       # warm up ATR14
    # up candle (OB)
    rows.append({"Open": 10.0, "High": 10.3, "Low": 9.95, "Close": 10.25, "Volume": 1_000})
    # impulse down
    rows.append({"Open": 10.2, "High": 10.2, "Low": 8.0, "Close": 8.1, "Volume": 3_000})
    df = _mk_df(rows)
    dets = detect_order_block(df, impulse_atr_mult=1.5)
    assert len(dets) == 1
    d = dets[0]
    assert d.pattern == "order_block" and d.bias == "bearish"
    assert d.bar_index == 15                    # the up candle before the impulse
    assert d.zone_low == 9.95 and d.zone_high == 10.3


def test_bearish_liquidity_sweep_detected():
    # prior 3-bar swing high = 11.0; bar wicks to 11.5 but closes back below at 10.8
    rows = [
        {"Open": 10.0, "High": 10.8, "Low": 9.9,  "Close": 10.5, "Volume": 1_000},
        {"Open": 10.5, "High": 11.0, "Low": 10.2, "Close": 10.7, "Volume": 1_000},
        {"Open": 10.7, "High": 10.9, "Low": 10.3, "Close": 10.6, "Volume": 1_000},
        {"Open": 10.6, "High": 11.5, "Low": 10.4, "Close": 10.8, "Volume": 2_000},  # sweep
    ]
    df = _mk_df(rows)
    dets = detect_liquidity_sweep(df, swing_lookback=3)
    assert len(dets) == 1
    d = dets[0]
    assert d.pattern == "liquidity_sweep" and d.bias == "bearish" and d.bar_index == 3
    assert d.zone_low == 11.0 and d.zone_high == 11.0     # swept level


def test_no_sweep_when_close_holds_breakout():
    rows = [
        {"Open": 10.0, "High": 10.8, "Low": 9.9,  "Close": 10.5, "Volume": 1_000},
        {"Open": 10.5, "High": 11.0, "Low": 10.2, "Close": 10.7, "Volume": 1_000},
        {"Open": 10.7, "High": 10.9, "Low": 10.3, "Close": 10.6, "Volume": 1_000},
        {"Open": 10.6, "High": 11.5, "Low": 10.4, "Close": 11.4, "Volume": 2_000},  # closes above
    ]
    df = _mk_df(rows)
    assert detect_liquidity_sweep(df, swing_lookback=3) == []


def test_bullish_liquidity_sweep_detected():
    # prior 3-bar swing low = 10.0; bar wicks to 9.5 but closes back above at 10.2
    rows = [
        {"Open": 10.5, "High": 10.8, "Low": 10.2, "Close": 10.5, "Volume": 1_000},
        {"Open": 10.4, "High": 10.6, "Low": 10.0, "Close": 10.3, "Volume": 1_000},
        {"Open": 10.3, "High": 10.5, "Low": 10.1, "Close": 10.4, "Volume": 1_000},
        {"Open": 10.4, "High": 10.6, "Low": 9.5,  "Close": 10.2, "Volume": 2_000},  # sweep
    ]
    df = _mk_df(rows)
    dets = detect_liquidity_sweep(df, swing_lookback=3)
    assert len(dets) == 1
    d = dets[0]
    assert d.pattern == "liquidity_sweep" and d.bias == "bullish" and d.bar_index == 3
    assert d.zone_low == 10.0 and d.zone_high == 10.0     # swept level


def test_outside_bar_sweeps_both_sides():
    # prior 3-bar high = 11.0, low = 10.0; final bar wicks beyond both but
    # closes back inside (below 11.0 and above 10.0) → both sweeps fire.
    rows = [
        {"Open": 10.5, "High": 10.8, "Low": 10.2, "Close": 10.5, "Volume": 1_000},
        {"Open": 10.5, "High": 11.0, "Low": 10.0, "Close": 10.7, "Volume": 1_000},
        {"Open": 10.7, "High": 10.9, "Low": 10.3, "Close": 10.6, "Volume": 1_000},
        {"Open": 10.6, "High": 11.5, "Low": 9.5,  "Close": 10.5, "Volume": 2_000},  # outside bar
    ]
    df = _mk_df(rows)
    dets = detect_liquidity_sweep(df, swing_lookback=3)
    biases = {d.bias for d in dets}
    assert biases == {"bearish", "bullish"}
    assert all(d.bar_index == 3 for d in dets)


def test_detect_all_combines_detectors():
    df = _mk_df([
        {"Open": 10.0, "High": 10.5, "Low": 9.5,  "Close": 10.0, "Volume": 1_000},
        {"Open": 10.5, "High": 12.0, "Low": 10.4, "Close": 11.8, "Volume": 2_000},
        {"Open": 11.9, "High": 12.5, "Low": 10.8, "Close": 12.2, "Volume": 1_500},
    ])
    dets = detect_all(df, impulse_atr_mult=1.5, swing_lookback=5)
    patterns = {d.pattern for d in dets}
    assert "fvg" in patterns                       # the bullish FVG from Task 2
    assert all(isinstance(d, SMCDetection) for d in dets)
