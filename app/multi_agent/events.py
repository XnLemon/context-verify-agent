from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable

from app.multi_agent.protocol import PipelineEvent

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publishes pipeline events for visualization.

    Supports multiple backends:
    - Redis Pub/Sub (real-time, for frontend WebSocket relay)
    - In-memory callback (for testing/orchestrator)
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis = None
        self._callbacks: list[Callable[[PipelineEvent], None]] = []

    def subscribe(self, callback: Callable[[PipelineEvent], None]) -> None:
        self._callbacks.append(callback)

    def publish(self, event: PipelineEvent) -> None:
        for cb in self._callbacks:
            try:
                cb(event)
            except Exception as exc:
                logger.warning("Event callback failed: %s", exc)
        self._publish_redis(event)

    def _publish_redis(self, event: PipelineEvent) -> None:
        try:
            import redis as rd
            if self._redis is None:
                self._redis = rd.from_url(self._redis_url)
            channel = f"pipeline:{event.pipeline_id}:events"
            self._redis.publish(channel, event.model_dump_json())
        except Exception as exc:
            logger.debug("Redis publish failed (non-fatal): %s", exc)

    def close(self) -> None:
        if self._redis:
            self._redis.close()
