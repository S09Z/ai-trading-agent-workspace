"""Run a full agent cycle via the Orchestrator.

Usage:
    uv run python -m scripts.run_cycle
    make cycle
"""

import asyncio


async def main() -> None:
    from agents.orchestrator import OrchestratorAgent
    await OrchestratorAgent().run()


if __name__ == "__main__":
    asyncio.run(main())
