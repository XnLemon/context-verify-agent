from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.postgres_workbench_repository import PostgresWorkbenchRepository
from app.services.workbench_repository import WorkbenchRepository


def verify_migration(json_base_dir: str) -> dict:
    json_repo = WorkbenchRepository(base_dir=json_base_dir)
    pg_repo = PostgresWorkbenchRepository()

    json_contracts = json_repo.list_contracts()
    pg_contracts = pg_repo.list_contracts()

    json_contract_ids = sorted(item.id for item in json_contracts)
    pg_contract_ids = sorted(item.id for item in pg_contracts)

    mismatched_reviews: list[str] = []
    mismatched_chats: list[str] = []
    mismatched_histories: list[str] = []

    for contract_id in json_contract_ids:
        json_review = json_repo.get_review(contract_id)
        pg_review = pg_repo.get_review(contract_id)
        if bool(json_review) != bool(pg_review):
            mismatched_reviews.append(contract_id)

        json_chat_count = len(json_repo.get_chat_thread(contract_id).messages)
        pg_chat_count = len(pg_repo.get_chat_thread(contract_id).messages)
        if json_chat_count != pg_chat_count:
            mismatched_chats.append(contract_id)

        json_history_count = len(json_repo.get_history(contract_id).items)
        pg_history_count = len(pg_repo.get_history(contract_id).items)
        if json_history_count != pg_history_count:
            mismatched_histories.append(contract_id)

    return {
        "json_contract_count": len(json_contract_ids),
        "pg_contract_count": len(pg_contract_ids),
        "contract_ids_match": json_contract_ids == pg_contract_ids,
        "mismatched_reviews": mismatched_reviews,
        "mismatched_chats": mismatched_chats,
        "mismatched_histories": mismatched_histories,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify JSON->PostgreSQL migration consistency")
    parser.add_argument("--json-base-dir", default=".run/workbench")
    args = parser.parse_args()

    result = verify_migration(str(Path(args.json_base_dir)))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
