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
    grade_short: str | None
    grade_mid: str | None
    grade_long: str | None
    created_at: datetime


class SignalOutcomeOut(BaseModel):
    id: int
    signal_id: int
    ticker: str
    signal_type: str
    source_agent: str
    price_at_signal: float | None
    price_5d: float | None
    outcome_5d: str | None
    change_pct_5d: float | None
    created_at: datetime
    evaluated_at: datetime | None


class AgentAccuracy(BaseModel):
    agent: str
    total: int
    correct: int
    incorrect: int
    neutral: int
    accuracy_pct: float | None
