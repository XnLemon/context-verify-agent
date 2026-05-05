from __future__ import annotations

import uuid
from typing import Any, Literal

from app.multi_agent.config import MultiAgentConfig
from app.multi_agent.protocol import (
    AgentMode,
    GatewayRequest,
    GatewayResponse,
    PipelineEvent,
    PipelineState,
    PipelineStatus,
)


class GatewayRouter:
    """Lightweight router that classifies requests and dispatches to the appropriate team."""

    # Explicit review keywords — bypass LLM classification
    _REVIEW_KEYWORDS: frozenset[str] = frozenset({
        "审查", "校审", "审阅", "重新扫描", "扫描合同",
        "复核", "检查合同", "跑一遍审查", "全面审查", "详细审查",
    })
    _SIMPLE_KEYWORDS: frozenset[str] = frozenset({
        "简单看看", "快速", "大概", "简单看一下",
    })
    _DEEP_KEYWORDS: frozenset[str] = frozenset({
        "深度", "全面", "详细", "彻底", "逐条",
    })

    def __init__(self, config: MultiAgentConfig | None = None) -> None:
        self.config = config or MultiAgentConfig()

    def route(
        self,
        user_message: str,
        contract_id: str | None = None,
        explicit_mode: AgentMode | None = None,
        contract_clause_count: int = 0,
    ) -> GatewayResponse:
        request_id = str(uuid.uuid4())

        # 1. Explicit mode takes priority
        mode = explicit_mode or self._detect_mode(user_message, contract_clause_count)

        # 2. Detect team
        team = self._detect_team(user_message)

        # 3. Build response
        return GatewayResponse(
            request_id=request_id,
            mode=mode,
            team=team,
        )

    def create_pipeline_state(
        self, response: GatewayResponse, contract_id: str | None = None
    ) -> PipelineState:
        return PipelineState(
            pipeline_id=response.pipeline_id or str(uuid.uuid4()),
            contract_id=contract_id or "unknown",
            mode=response.mode,
            team=response.team,
            status=PipelineStatus.PENDING,
        )

    def _detect_mode(self, message: str, clause_count: int) -> AgentMode:
        msg_lower = message.lower()

        # Check for explicit simple/deep keywords
        if any(kw in msg_lower for kw in self._SIMPLE_KEYWORDS):
            return AgentMode.SINGLE
        if any(kw in msg_lower for kw in self._DEEP_KEYWORDS):
            return AgentMode.MULTI_MANUAL

        # Auto mode: decide based on complexity
        if clause_count > 50:
            return AgentMode.MULTI_MANUAL
        if clause_count > 20:
            return AgentMode.MULTI_AUTO

        return AgentMode.MULTI_AUTO

    def _detect_team(self, message: str) -> Literal["review", "dialogue"]:
        if any(kw in message for kw in self._REVIEW_KEYWORDS):
            return "review"
        return "dialogue"

    def create_pipeline_started_event(self, state: PipelineState) -> PipelineEvent:
        return PipelineEvent(
            pipeline_id=state.pipeline_id,
            event_type="pipeline_started",
            data={
                "contract_id": state.contract_id,
                "mode": state.mode.value,
                "team": state.team,
            },
        )
