"""Tests for the YAML swarm loader (PR #9)."""

from unittest.mock import AsyncMock, patch

import pytest

# ── Preset discovery ─────────────────────────────────────────────────────────────

def test_list_presets_returns_example_presets():
    from agents.swarm_loader import list_presets

    presets = list_presets()
    names = {p["name"] for p in presets}
    assert "Earnings Research Desk" in names
    assert "Quant Strategy Desk" in names

    earnings = next(p for p in presets if p["name"] == "Earnings Research Desk")
    assert earnings["filename"] == "earnings_desk"
    assert {a["id"] for a in earnings["agents"]} == {
        "fundamental", "sentiment", "risk", "research",
    }


def test_load_preset_returns_validated_spec():
    from agents.swarm_loader import load_preset

    spec = load_preset("earnings_desk")
    assert spec["name"] == "Earnings Research Desk"
    assert len(spec["agents"]) == 4


def test_load_preset_unknown_name_raises():
    from agents.swarm_loader import load_preset

    with pytest.raises(FileNotFoundError):
        load_preset("does_not_exist")


# ── Validation ───────────────────────────────────────────────────────────────────

def test_validate_spec_rejects_unknown_agent_type():
    from agents.swarm_loader import validate_spec

    spec = {"name": "x", "agents": [{"id": "a", "type": "NoSuchAgent", "depends_on": []}]}
    with pytest.raises(ValueError, match="unknown agent type"):
        validate_spec(spec)


def test_validate_spec_rejects_missing_dependency():
    from agents.swarm_loader import validate_spec

    spec = {
        "name": "x",
        "agents": [{"id": "a", "type": "RiskMonitor", "depends_on": ["ghost"]}],
    }
    with pytest.raises(ValueError, match="unknown dependency"):
        validate_spec(spec)


def test_validate_spec_rejects_duplicate_ids():
    from agents.swarm_loader import validate_spec

    spec = {
        "name": "x",
        "agents": [
            {"id": "a", "type": "RiskMonitor", "depends_on": []},
            {"id": "a", "type": "SentimentAnalyst", "depends_on": []},
        ],
    }
    with pytest.raises(ValueError, match="duplicate"):
        validate_spec(spec)


def test_cycle_is_rejected():
    from agents.swarm_loader import _topological_levels

    agents = [
        {"id": "a", "type": "RiskMonitor", "depends_on": ["b"]},
        {"id": "b", "type": "SentimentAnalyst", "depends_on": ["a"]},
    ]
    with pytest.raises(ValueError, match="cycle"):
        _topological_levels(agents)


# ── Topological ordering ─────────────────────────────────────────────────────────

def test_topological_levels_groups_independent_nodes():
    from agents.swarm_loader import _topological_levels

    agents = [
        {"id": "a", "type": "FinancialAnalyst", "depends_on": []},
        {"id": "b", "type": "SentimentAnalyst", "depends_on": []},
        {"id": "c", "type": "RiskMonitor", "depends_on": ["a", "b"]},
        {"id": "d", "type": "ResearchAnalyst", "depends_on": ["c"]},
    ]
    levels = _topological_levels(agents)
    ids = [[n["id"] for n in level] for level in levels]

    assert set(ids[0]) == {"a", "b"}
    assert ids[1] == ["c"]
    assert ids[2] == ["d"]


# ── run_swarm execution ──────────────────────────────────────────────────────────

_LINEAR_SPEC = {
    "name": "Linear",
    "agents": [
        {"id": "one", "type": "FinancialAnalyst", "depends_on": []},
        {"id": "two", "type": "ResearchAnalyst", "depends_on": ["one"]},
        {"id": "three", "type": "RiskMonitor", "depends_on": ["two"]},
    ],
}


async def test_run_swarm_executes_in_dependency_order():
    from agents.swarm_loader import run_swarm

    order: list[str] = []

    def rec(label):
        async def _run(self, *a, **k):
            order.append(label)
        return _run

    with patch("agents.swarm_loader.load_preset", return_value=_LINEAR_SPEC), \
         patch("agents.base.BaseAgent.log", new=AsyncMock()), \
         patch("agents.financial_analyst.FinancialAnalystAgent.run", new=rec("one")), \
         patch("agents.research_analyst.ResearchAnalystAgent.run", new=rec("two")), \
         patch("agents.risk_monitor.RiskMonitorAgent.run", new=rec("three")):
        await run_swarm("linear")

    assert order == ["one", "two", "three"]


async def test_run_swarm_logs_start_and_complete():
    from agents.swarm_loader import run_swarm

    log = AsyncMock()
    with patch("agents.swarm_loader.load_preset", return_value=_LINEAR_SPEC), \
         patch("agents.base.BaseAgent.log", new=log), \
         patch("agents.financial_analyst.FinancialAnalystAgent.run", new=AsyncMock()), \
         patch("agents.research_analyst.ResearchAnalystAgent.run", new=AsyncMock()), \
         patch("agents.risk_monitor.RiskMonitorAgent.run", new=AsyncMock()):
        await run_swarm("linear")

    actions = [call.args[0] for call in log.await_args_list]
    assert "swarm_start" in actions
    assert "swarm_complete" in actions


async def test_run_swarm_isolates_node_errors():
    from agents.swarm_loader import run_swarm

    downstream = AsyncMock()
    log = AsyncMock()
    with patch("agents.swarm_loader.load_preset", return_value=_LINEAR_SPEC), \
         patch("agents.base.BaseAgent.log", new=log), \
         patch("agents.financial_analyst.FinancialAnalystAgent.run",
               new=AsyncMock(side_effect=RuntimeError("boom"))), \
         patch("agents.research_analyst.ResearchAnalystAgent.run", new=downstream), \
         patch("agents.risk_monitor.RiskMonitorAgent.run", new=AsyncMock()):
        await run_swarm("linear")

    # A failing node is logged and does not abort the swarm.
    actions = [call.args[0] for call in log.await_args_list]
    assert "swarm_error" in actions
    downstream.assert_awaited_once()
