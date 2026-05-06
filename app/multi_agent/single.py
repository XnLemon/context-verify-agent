from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.multi_agent.protocol import AgentMode, PipelineState, PipelineStatus
from app.services.review_service import ReviewService
from app.schemas.review import ReviewRequest


class SingleAgentHandler:
    """Handles single-agent mode: direct LLM call, no pipeline overhead."""

    def __init__(self) -> None:
        self.review_service = ReviewService()

    def run_review(
        self,
        state: PipelineState,
        contract_text: str,
        contract_type: str | None = None,
        our_side: str = "甲方",
    ) -> tuple[PipelineState, dict[str, Any]]:
        state.status = PipelineStatus.RUNNING
        try:
            result = self.review_service.review(
                ReviewRequest(
                    contract_text=contract_text,
                    contract_type=contract_type,
                    our_side=our_side,
                )
            )
            state.status = PipelineStatus.COMPLETED
            state.completed_at = datetime.now(timezone.utc)
            return state, {"review_result": result.model_dump(mode="json")}
        except Exception as exc:
            state.status = PipelineStatus.FAILED
            state.errors.append({"agent_id": "single_agent", "error": str(exc)})
            state.completed_at = datetime.now(timezone.utc)
            return state, {"error": str(exc)}
