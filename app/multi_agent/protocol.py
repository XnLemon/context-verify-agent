from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentMode(str, Enum):
    SINGLE = "single"
    MULTI_AUTO = "multi_auto"
    MULTI_MANUAL = "multi_manual"


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class AgentFinding(BaseModel):
    clause: str
    risk: Literal["high", "medium", "low", "info"]
    summary: str
    suggestion: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


class AgentOutput(BaseModel):
    agent_id: str
    status: AgentStatus
    input_summary: str = ""
    findings: list[AgentFinding] = Field(default_factory=list)
    structured_data: dict[str, Any] = Field(default_factory=dict)
    next_agent_hints: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    token_used: int = 0


class PipelineState(BaseModel):
    pipeline_id: str
    contract_id: str
    mode: AgentMode
    team: Literal["review", "dialogue"]
    status: PipelineStatus
    current_agent: str | None = None
    agent_outputs: dict[str, AgentOutput] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    token_used_total: int = 0


class GatewayRequest(BaseModel):
    request_id: str
    team: Literal["review", "dialogue"]
    mode: AgentMode
    contract_id: str | None = None
    user_message: str = ""
    context_ids: list[str] = Field(default_factory=list)


class GatewayResponse(BaseModel):
    request_id: str
    pipeline_id: str | None = None
    mode: AgentMode
    team: Literal["review", "dialogue"]
    error: str | None = None


class PipelineEvent(BaseModel):
    pipeline_id: str
    event_type: Literal[
        "pipeline_started", "pipeline_completed", "pipeline_failed",
        "agent_started", "agent_completed", "agent_failed", "agent_skipped",
        "pipeline_cancelled", "compression_triggered",
    ]
    agent_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
