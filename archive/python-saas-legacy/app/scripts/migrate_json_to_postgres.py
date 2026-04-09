from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.postgres_workbench_repository import PostgresWorkbenchRepository
from app.services.workbench_repository import WorkbenchRepository


def migrate_workbench(json_base_dir: str) -> dict[str, int]:
    json_repo = WorkbenchRepository(base_dir=json_base_dir)
    pg_repo = PostgresWorkbenchRepository()

    contracts = json_repo.list_contracts()
    for contract in contracts:
        pg_repo.save_contract(contract)

    migrated_reviews = 0
    migrated_threads = 0
    migrated_histories = 0
    for contract in contracts:
        review = json_repo.get_review(contract.id)
        if review is not None:
            pg_repo.save_review(review)
            migrated_reviews += 1

        thread = json_repo.get_chat_thread(contract.id)
        if thread.messages:
            pg_repo.save_chat_thread(thread)
            migrated_threads += 1

        history = json_repo.get_history(contract.id)
        if history.items:
            pg_repo.save_history(history)
            migrated_histories += 1

    return {
        "contracts": len(contracts),
        "reviews": migrated_reviews,
        "chat_threads": migrated_threads,
        "history_logs": migrated_histories,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate local workbench JSON data into PostgreSQL")
    parser.add_argument("--json-base-dir", default=".run/workbench")
    args = parser.parse_args()

    base_dir = Path(args.json_base_dir)
    result = migrate_workbench(str(base_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
