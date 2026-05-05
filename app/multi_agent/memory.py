from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import redis

from app.core.config import settings
from app.multi_agent.config import MultiAgentConfig
from app.multi_agent.protocol import AgentOutput, PipelineState

logger = logging.getLogger(__name__)


class HotLayer:
    """Redis-backed hot layer: current pipeline state + recent dialogue rounds."""

    def __init__(self, config: MultiAgentConfig) -> None:
        self.config = config
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.config.redis_url, decode_responses=True)
        return self._client

    def set_pipeline_state(self, state: PipelineState) -> None:
        key = f"pipeline:{state.pipeline_id}"
        self.client.setex(key, self.config.redis_ttl_seconds, state.model_dump_json())

    def get_pipeline_state(self, pipeline_id: str) -> PipelineState | None:
        key = f"pipeline:{pipeline_id}"
        raw = self.client.get(key)
        if not raw:
            return None
        return PipelineState.model_validate_json(raw)

    def set_agent_output(self, pipeline_id: str, output: AgentOutput) -> None:
        key = f"agent_output:{pipeline_id}:{output.agent_id}"
        self.client.setex(key, self.config.redis_ttl_seconds, output.model_dump_json())

    def get_agent_output(self, pipeline_id: str, agent_id: str) -> AgentOutput | None:
        key = f"agent_output:{pipeline_id}:{agent_id}"
        raw = self.client.get(key)
        if not raw:
            return None
        return AgentOutput.model_validate_json(raw)

    def delete_pipeline(self, pipeline_id: str) -> None:
        self.client.delete(f"pipeline:{pipeline_id}")

    def refresh_ttl(self, pipeline_id: str) -> None:
        self.client.expire(f"pipeline:{pipeline_id}", self.config.redis_ttl_seconds)

    def close(self) -> None:
        if self._client:
            self._client.close()


class WarmLayer:
    """PostgreSQL-backed warm layer: structured agent outputs and conversation history."""

    def save_pipeline_outputs(
        self, pipeline_id: str, contract_id: str,
        agent_outputs: dict[str, AgentOutput],
    ) -> None:
        from app.db.session import SessionLocal
        from app.db.multi_agent_models import AgentOutputRecord

        db = SessionLocal()
        try:
            for agent_id, output in agent_outputs.items():
                record = AgentOutputRecord(
                    pipeline_id=pipeline_id,
                    contract_id=contract_id,
                    agent_id=agent_id,
                    status=output.status.value,
                    output_json=output.model_dump(mode="json"),
                    created_at=datetime.now(timezone.utc),
                )
                db.add(record)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_review_results(self, contract_id: str) -> dict[str, Any] | None:
        from app.db.session import SessionLocal
        from app.db.multi_agent_models import AgentOutputRecord

        db = SessionLocal()
        try:
            record = (
                db.query(AgentOutputRecord)
                .filter(
                    AgentOutputRecord.contract_id == contract_id,
                    AgentOutputRecord.agent_id == "summarizer",
                    AgentOutputRecord.status == "completed",
                )
                .order_by(AgentOutputRecord.created_at.desc())
                .first()
            )
            if record and record.output_json:
                return record.output_json.get("structured_data", {}).get("review_report")
            return None
        finally:
            db.close()

    def get_agent_outputs_for_contract(
        self, contract_id: str, agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        from app.db.session import SessionLocal
        from app.db.multi_agent_models import AgentOutputRecord

        db = SessionLocal()
        try:
            q = db.query(AgentOutputRecord).filter(
                AgentOutputRecord.contract_id == contract_id
            )
            if agent_id:
                q = q.filter(AgentOutputRecord.agent_id == agent_id)
            records = q.order_by(AgentOutputRecord.created_at.desc()).limit(20).all()
            return [r.output_json for r in records if r.output_json]
        finally:
            db.close()


class ColdLayer:
    """Milvus-backed cold layer: historical data for semantic retrieval."""

    def is_available(self) -> bool:
        try:
            from app.rag.vector_store import is_knowledge_base_ready
            return is_knowledge_base_ready(settings.knowledge_vector_store_dir)
        except Exception:
            return False

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if not self.is_available():
            return []
        try:
            from app.rag.vector_store import load_vector_store
            from app.rag.retriever import ContractKnowledgeRetriever
            store = load_vector_store(settings.knowledge_vector_store_dir)
            retriever = ContractKnowledgeRetriever(store)
            docs = retriever.retrieve_documents(query=query, k=top_k)
            return [
                {
                    "content": doc.page_content[:300],
                    "source": doc.metadata.get("title", "未知"),
                    "score": doc.metadata.get("score", 0),
                }
                for doc in docs
            ]
        except Exception as exc:
            logger.warning("Cold layer search failed: %s", exc)
            return []


class MemoryManager:
    """Unified access to all three memory tiers."""

    def __init__(self, config: MultiAgentConfig | None = None) -> None:
        self.config = config or MultiAgentConfig()
        self.hot = HotLayer(self.config)
        self.warm = WarmLayer()
        self.cold = ColdLayer()

    def save_pipeline_result(self, state: PipelineState) -> None:
        self.hot.set_pipeline_state(state)
        self.warm.save_pipeline_outputs(
            pipeline_id=state.pipeline_id,
            contract_id=state.contract_id,
            agent_outputs=state.agent_outputs,
        )

    def get_review_context(self, contract_id: str) -> dict[str, Any] | None:
        return self.warm.get_review_results(contract_id)

    def close(self) -> None:
        self.hot.close()
