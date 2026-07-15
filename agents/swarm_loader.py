"""YAML-configurable agent swarms (PR #9).

A "swarm preset" is a YAML file under ``config/swarm_presets/`` that lists agents
and their ``depends_on`` ordering. The loader validates the preset, computes
topological execution levels, and runs each level's agents in parallel — a
data-driven generalisation of the hard-coded layers in ``agents/orchestrator.py``.

Agents in this codebase communicate through the database (AgentLog / Signal), not
via return values, so ``depends_on`` controls execution *ordering* only. The YAML
``skills`` and ``output`` fields are parsed but have no runtime effect yet.
"""

import asyncio
from pathlib import Path

import yaml

from agents.base import BaseAgent
from agents.discovery_agent import DiscoveryAgent
from agents.financial_analyst import FinancialAnalystAgent
from agents.market_watch import MarketWatchAgent
from agents.memory_agent import MemoryAgent
from agents.news_hunter import NewsHunterAgent
from agents.research_analyst import ResearchAnalystAgent
from agents.risk_monitor import RiskMonitorAgent
from agents.sentiment_analyst import SentimentAnalystAgent

# Map YAML ``type`` → agent class. Orchestrator is intentionally excluded — it is
# the swarm runner, not a leaf agent.
AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "NewsHunter": NewsHunterAgent,
    "MarketWatch": MarketWatchAgent,
    "SentimentAnalyst": SentimentAnalystAgent,
    "RiskMonitor": RiskMonitorAgent,
    "ResearchAnalyst": ResearchAnalystAgent,
    "FinancialAnalyst": FinancialAnalystAgent,
    "Discovery": DiscoveryAgent,
    "Memory": MemoryAgent,
}

PRESETS_DIR = Path(__file__).resolve().parent.parent / "config" / "swarm_presets"


def list_presets(presets_dir: Path = PRESETS_DIR) -> list[dict]:
    """Return all presets as ``{name, description, filename, agents}`` dicts."""
    presets = []
    for path in sorted(presets_dir.glob("*.yaml")):
        spec = yaml.safe_load(path.read_text())
        presets.append({
            "name": spec.get("name", path.stem),
            "description": spec.get("description", ""),
            "filename": path.stem,
            "agents": spec.get("agents", []),
        })
    return presets


def load_preset(name: str, presets_dir: Path = PRESETS_DIR) -> dict:
    """Load and validate a single preset by filename stem (e.g. ``earnings_desk``)."""
    path = presets_dir / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"swarm preset not found: {name}")
    spec = yaml.safe_load(path.read_text())
    validate_spec(spec)
    return spec


def validate_spec(spec: dict) -> None:
    """Raise ValueError if the spec references unknown types, deps, or dup ids."""
    agents = spec.get("agents", [])
    ids = [a["id"] for a in agents]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate agent id in preset {spec.get('name')!r}")
    known = set(ids)
    for a in agents:
        if a["type"] not in AGENT_REGISTRY:
            raise ValueError(
                f"unknown agent type {a['type']!r} (node {a['id']!r}); "
                f"valid types: {sorted(AGENT_REGISTRY)}"
            )
        for dep in a.get("depends_on", []):
            if dep not in known:
                raise ValueError(
                    f"unknown dependency {dep!r} for node {a['id']!r}"
                )
    # Surface cycles eagerly so load_preset fails fast.
    _topological_levels(agents)


def _topological_levels(agents: list[dict]) -> list[list[dict]]:
    """Group nodes into execution levels via Kahn's algorithm.

    Each level contains nodes whose dependencies are all satisfied by earlier
    levels; nodes within a level are independent and run in parallel. Raises
    ValueError if the graph contains a cycle.
    """
    by_id = {a["id"]: a for a in agents}
    remaining = {a["id"]: set(a.get("depends_on", [])) for a in agents}
    levels: list[list[dict]] = []

    while remaining:
        ready = sorted(nid for nid, deps in remaining.items() if not deps)
        if not ready:
            raise ValueError(f"dependency cycle among nodes: {sorted(remaining)}")
        levels.append([by_id[nid] for nid in ready])
        for nid in ready:
            del remaining[nid]
        for deps in remaining.values():
            deps.difference_update(ready)

    return levels


class SwarmRunner(BaseAgent):
    """Runs a swarm preset, logging progress to AgentLog for the Virtual Office."""

    name = "swarm"

    def __init__(self, preset: str) -> None:
        self.preset = preset

    async def run(self) -> None:
        spec = load_preset(self.preset)
        levels = _topological_levels(spec["agents"])
        await self.log(
            "swarm_start",
            f"{spec['name']} — {len(spec['agents'])} agents in {len(levels)} levels",
            meta={"preset": self.preset},
        )

        for level in levels:
            await asyncio.gather(*[self._run_node(node) for node in level])

        await self.log("swarm_complete", f"{spec['name']} finished")

    async def _run_node(self, node: dict) -> None:
        agent_cls = AGENT_REGISTRY[node["type"]]
        try:
            await self.log("swarm_node", f"{node['id']} ({node['type']}) start")
            await agent_cls().run()
        except Exception as exc:  # one failed node must not abort the swarm
            await self.log(
                "swarm_error", f"{node['id']} failed: {exc}", level="error"
            )


async def run_swarm(preset: str) -> None:
    """Entry point: run a swarm preset by filename stem."""
    await SwarmRunner(preset).run()
