"""Agent Cockpit — FastAPI application."""

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text

from cockpit.routers import agents, logs, outcomes, signals
from config.settings import get_settings
from memory.database import AsyncSessionLocal

app = FastAPI(title="AlphaOps Agent Cockpit", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(signals.router, prefix="/signals", tags=["signals"])
app.include_router(logs.router, prefix="/logs", tags=["logs"])
app.include_router(outcomes.router, prefix="/outcomes", tags=["outcomes"])

Instrumentator().instrument(app).expose(app, include_in_schema=False)


@app.get("/health")
async def health() -> dict:
    settings = get_settings()
    checks: dict[str, str] = {}

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "error"

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                f"http://{settings.qdrant_host}:{settings.qdrant_port}/"
            )
        checks["qdrant"] = "ok" if resp.status_code == 200 else "error"
    except Exception:
        checks["qdrant"] = "error"

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, **checks}
