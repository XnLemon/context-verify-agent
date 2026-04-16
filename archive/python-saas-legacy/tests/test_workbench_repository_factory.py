import unittest
from unittest.mock import patch

from app.core.config import settings
from app.services.workbench_repository_factory import build_workbench_repository


class WorkbenchRepositoryFactoryTests(unittest.TestCase):
    def test_factory_returns_postgres_when_backend_is_postgres(self) -> None:
        original_backend = settings.workbench_backend
        original_dsn = settings.postgres_dsn
        settings.workbench_backend = "postgres"
        settings.postgres_dsn = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/contract_agent"
        with patch("app.services.workbench_repository_factory.PostgresWorkbenchRepository") as repo_cls:
            sentinel_repo = object()
            repo_cls.return_value = sentinel_repo
            try:
                repo = build_workbench_repository()
            finally:
                settings.workbench_backend = original_backend
                settings.postgres_dsn = original_dsn

        self.assertIs(repo, sentinel_repo)

    def test_factory_warns_and_forces_postgres_for_deprecated_backend(self) -> None:
        original_backend = settings.workbench_backend
        original_dsn = settings.postgres_dsn
        settings.workbench_backend = "dual_write"
        settings.postgres_dsn = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/contract_agent"
        with patch("app.services.workbench_repository_factory.PostgresWorkbenchRepository") as repo_cls:
            repo_cls.return_value = object()
            with self.assertLogs("app.services.workbench_repository_factory", level="WARNING") as logs:
                try:
                    build_workbench_repository()
                finally:
                    settings.workbench_backend = original_backend
                    settings.postgres_dsn = original_dsn

        self.assertTrue(any("已废弃" in record for record in logs.output))

    def test_factory_warns_and_forces_postgres_for_unknown_backend(self) -> None:
        original_backend = settings.workbench_backend
        original_dsn = settings.postgres_dsn
        settings.workbench_backend = "memory"
        settings.postgres_dsn = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/contract_agent"
        with patch("app.services.workbench_repository_factory.PostgresWorkbenchRepository") as repo_cls:
            repo_cls.return_value = object()
            with self.assertLogs("app.services.workbench_repository_factory", level="WARNING") as logs:
                try:
                    build_workbench_repository()
                finally:
                    settings.workbench_backend = original_backend
                    settings.postgres_dsn = original_dsn

        self.assertTrue(any("不受支持" in record for record in logs.output))

    def test_factory_raises_for_missing_postgres_dsn(self) -> None:
        original_backend = settings.workbench_backend
        original_dsn = settings.postgres_dsn
        settings.workbench_backend = "postgres"
        settings.postgres_dsn = None
        try:
            with self.assertRaises(RuntimeError):
                build_workbench_repository()
        finally:
            settings.workbench_backend = original_backend
            settings.postgres_dsn = original_dsn


if __name__ == "__main__":
    unittest.main()
