"""Agent Cockpit — FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cockpit.routers import agents, logs, signals

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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
