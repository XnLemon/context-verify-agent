from __future__ import annotations

import logging

from app.core.config import settings
from app.services.postgres_workbench_repository import PostgresWorkbenchRepository
from app.services.workbench_repository_interface import IWorkbenchRepository

_DEPRECATED_BACKENDS = {"json", "dual_write"}
logger = logging.getLogger(__name__)


def build_workbench_repository() -> IWorkbenchRepository:
    backend = (settings.workbench_backend or "postgres").strip().lower()
    if backend in _DEPRECATED_BACKENDS:
        logger.warning(
            "WORKBENCH_BACKEND=%s 已废弃，运行时已强制切换为 postgres。",
            backend,
        )
    elif backend and backend != "postgres":
        logger.warning(
            "WORKBENCH_BACKEND=%s 不受支持，运行时已强制切换为 postgres。",
            backend,
        )

    if not settings.postgres_dsn:
        raise RuntimeError("POSTGRES_DSN 未配置，运行时仅支持 postgres 持久化。")

    return PostgresWorkbenchRepository()
