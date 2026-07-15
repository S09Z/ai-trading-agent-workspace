"""Swarm preset endpoints (PR #9)."""

from fastapi import APIRouter, HTTPException

from agents.swarm_loader import list_presets, load_preset

router = APIRouter()


@router.get("/presets")
async def get_presets() -> list[dict]:
    """List available swarm presets."""
    return list_presets()


@router.post("/run/{preset}")
async def run_preset(preset: str) -> dict:
    """Validate a preset and enqueue it for asynchronous execution."""
    try:
        load_preset(preset)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"unknown preset: {preset}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    from scheduler.tasks import celery_app

    celery_app.send_task("scheduler.tasks.run_swarm", args=[preset])
    return {"status": "queued", "preset": preset}
