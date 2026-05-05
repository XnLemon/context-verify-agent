from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from app.multi_agent.config import MultiAgentConfig
from app.multi_agent.protocol import (
    AgentOutput,
    AgentStatus,
    PipelineEvent,
    PipelineState,
    PipelineStatus,
)


AgentFn = Callable[[dict[str, Any]], AgentOutput]


class PipelineOrchestrator:
    """Orchestrates a sequence of agents as a LangGraph-inspired pipeline.

    For v1, this is a sequential pipeline with conditional routing and error recovery.
    Future versions may adopt LangGraph's StateGraph directly.
    """

    def __init__(self, config: MultiAgentConfig | None = None) -> None:
        self.config = config or MultiAgentConfig()
        self._agents: dict[str, AgentFn] = {}
        self._routes: dict[str, list[tuple[str, str]]] = {}

    def register_agent(self, agent_id: str, fn: AgentFn) -> None:
        self._agents[agent_id] = fn

    def register_route(
        self, from_agent: str, condition: str, to_agent: str
    ) -> None:
        if from_agent not in self._routes:
            self._routes[from_agent] = []
        self._routes[from_agent].append((to_agent, condition))

    def register_fallback(self, agent_id: str, fallback_agent: str | None = None) -> None:
        target = fallback_agent or "__skip__"
        self._routes.setdefault(agent_id, []).append((target, "__fallback__"))

    def run(
        self,
        state: PipelineState,
        initial_input: dict[str, Any],
        on_event: Callable[[PipelineEvent], None] | None = None,
    ) -> PipelineState:
        state.status = PipelineStatus.RUNNING
        self._emit(on_event, self._event(state, "pipeline_started"))

        ctx = dict(initial_input)
        agent_queue = list(self._build_queue(state.team))
        skipped_agents: set[str] = set()
        idx = 0

        while idx < len(agent_queue):
            agent_id = agent_queue[idx]
            idx += 1

            if state.status == PipelineStatus.CANCELLED:
                break

            if agent_id in skipped_agents:
                continue

            state.current_agent = agent_id
            agent_fn = self._agents.get(agent_id)
            if not agent_fn:
                continue

            self._emit(on_event, self._event(state, "agent_started", agent_id))

            try:
                output = agent_fn(ctx)
            except Exception as exc:
                output = AgentOutput(
                    agent_id=agent_id,
                    status=AgentStatus.FAILED,
                    error_message=str(exc),
                )
                state.errors.append({"agent_id": agent_id, "error": str(exc)})
                self._emit(on_event, self._event(state, "agent_failed", agent_id, {"error": str(exc)}))

                next_target = self._resolve_fallback(agent_id)
                if next_target == "__abort__":
                    state.status = PipelineStatus.FAILED
                    break
                if next_target == "__skip__":
                    skipped_agents.add(agent_id)
                    continue
                # Replace current agent's slot with fallback (don't advance counter)
                agent_queue[idx - 1] = next_target
                idx -= 1
                continue

            state.agent_outputs[agent_id] = output
            ctx.update(output.structured_data)
            state.token_used_total += output.token_used

            self._emit(on_event, self._event(state, "agent_completed", agent_id, {
                "findings_count": len(output.findings),
                "token_used": output.token_used,
                "status": output.status.value,
            }))

        if state.status not in (PipelineStatus.FAILED, PipelineStatus.CANCELLED):
            state.status = PipelineStatus.COMPLETED
        state.completed_at = datetime.now(timezone.utc)

        closing_event = {
            PipelineStatus.COMPLETED: "pipeline_completed",
            PipelineStatus.FAILED: "pipeline_failed",
            PipelineStatus.CANCELLED: "pipeline_cancelled",
        }.get(state.status, "pipeline_completed")
        self._emit(on_event, self._event(state, closing_event))
        return state

    def cancel(self, state: PipelineState) -> None:
        state.status = PipelineStatus.CANCELLED

    def _build_queue(self, team: str) -> list[str]:
        if team == "review":
            return ["parser", "risk_checker", "legal_ref", "redrafter", "summarizer"]
        return ["qa", "clarifier", "legal_explain", "comparer", "researcher"]

    def _resolve_fallback(self, agent_id: str) -> str:
        routes = self._routes.get(agent_id, [])
        for target, condition in routes:
            if condition == "__fallback__":
                return target
        return "__abort__"

    def _emit(
        self,
        on_event: Callable[[PipelineEvent], None] | None,
        event: PipelineEvent,
    ) -> None:
        if on_event:
            on_event(event)

    def _event(
        self,
        state: PipelineState,
        event_type: str,
        agent_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> PipelineEvent:
        data = {"contract_id": state.contract_id, "mode": state.mode.value}
        if extra:
            data.update(extra)
        return PipelineEvent(
            pipeline_id=state.pipeline_id,
            event_type=event_type,  # type: ignore[arg-type]
            agent_id=agent_id,
            data=data,
        )
