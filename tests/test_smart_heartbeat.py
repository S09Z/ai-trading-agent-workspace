"""Tests for the Smart Heartbeat notify gate — pure unit, no DB."""

from intelligence.summarizer import HeartbeatDecision, should_notify

_NO_RISK = {"circuit_open": False, "spike_count": 0, "alert_count": 0}


def _sig(**kw):
    base = {"ticker": "X", "signal_type": "watchlist", "confidence": 0.5,
            "grade_short": None, "composite_score": None}
    base.update(kw)
    return base


def test_notify_when_circuit_open():
    risk = {"circuit_open": True, "spike_count": 0, "alert_count": 0}
    decision, _ = should_notify(3, [], risk)
    assert decision is HeartbeatDecision.NOTIFY


def test_notify_when_spike_count_positive():
    risk = {"circuit_open": False, "spike_count": 2, "alert_count": 0}
    decision, _ = should_notify(3, [], risk)
    assert decision is HeartbeatDecision.NOTIFY


def test_notify_when_directional_signal_bullish():
    decision, _ = should_notify(3, [_sig(signal_type="bullish", confidence=0.3)], _NO_RISK)
    assert decision is HeartbeatDecision.NOTIFY


def test_notify_when_directional_signal_bearish():
    decision, _ = should_notify(3, [_sig(signal_type="bearish", confidence=0.3)], _NO_RISK)
    assert decision is HeartbeatDecision.NOTIFY


def test_notify_when_high_confidence_watchlist():
    decision, _ = should_notify(3, [_sig(signal_type="watchlist", confidence=0.7)], _NO_RISK)
    assert decision is HeartbeatDecision.NOTIFY


def test_notify_when_grade_a_signal():
    decision, _ = should_notify(
        3, [_sig(signal_type="watchlist", confidence=0.4, grade_short="A")], _NO_RISK
    )
    assert decision is HeartbeatDecision.NOTIFY


def test_notify_when_grade_s_signal():
    decision, _ = should_notify(
        3, [_sig(signal_type="watchlist", confidence=0.4, grade_short="S")], _NO_RISK
    )
    assert decision is HeartbeatDecision.NOTIFY


def test_skip_when_no_signals_no_risk():
    decision, reason = should_notify(3, [], _NO_RISK)
    assert decision is HeartbeatDecision.SKIP
    assert reason


def test_skip_when_only_low_confidence_watchlist():
    decision, _ = should_notify(
        3, [_sig(signal_type="watchlist", confidence=0.4, grade_short=None)], _NO_RISK
    )
    assert decision is HeartbeatDecision.SKIP


def test_heartbeat_decision_is_str_enum():
    assert HeartbeatDecision.NOTIFY.value == "notify"
    assert HeartbeatDecision.SKIP.value == "skip"
