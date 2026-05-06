from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MultiAgentConfig:
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_seconds: int = 1800
    max_retries_per_agent: int = 1
    pipeline_timeout_seconds: int = 300
    agent_timeout_seconds: int = 30
    hot_layer_rounds: int = 3
    warm_layer_rounds: int = 10
    context_warn_threshold: float = 0.6
    context_compress_threshold: float = 0.75
    context_force_threshold: float = 0.9
    milvus_retry_max: int = 3
