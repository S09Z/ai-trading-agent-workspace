"""Pydantic response schemas for the Agent Cockpit API."""

from datetime import datetime

from pydantic import BaseModel


class AgentStatus(BaseModel):
    name: str
    last_action: str | None
    last_message: str | None
    last_seen: datetime | None
    level: str  # info | warning | error


class LogEntry(BaseModel):
    id: int
    agent_name: str
    action: str
    message: str
    level: str
    created_at: datetime


class SignalOut(BaseModel):
    id: int
    ticker: str
    signal_type: str
    confidence: float
    source_agent: str
    rationale: str | None
    created_at: datetime
