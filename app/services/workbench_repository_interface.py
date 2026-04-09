from __future__ import annotations

from typing import Protocol

from app.schemas.workbench import StoredChatThread, StoredHistoryLog, StoredReviewRecord, WorkbenchContract, WorkbenchHistoryItem


class IWorkbenchRepository(Protocol):
    def list_contracts(self) -> list[WorkbenchContract]:
        ...

    def get_contract(self, contract_id: str) -> WorkbenchContract | None:
        ...

    def save_contract(self, contract: WorkbenchContract) -> None:
        ...

    def get_review(self, contract_id: str) -> StoredReviewRecord | None:
        ...

    def save_review(self, review: StoredReviewRecord) -> None:
        ...

    def get_chat_thread(self, contract_id: str, member_id: int = 0) -> StoredChatThread:
        ...

    def save_chat_thread(self, thread: StoredChatThread, member_id: int = 0) -> None:
        ...

    def get_history(self, contract_id: str, member_id: int = 0) -> StoredHistoryLog:
        ...

    def save_history(self, history: StoredHistoryLog, member_id: int = 0) -> None:
        ...

    def append_history_item(self, contract_id: str, item: WorkbenchHistoryItem, member_id: int = 0) -> StoredHistoryLog:
        ...

    def create_contract(
        self,
        *,
        title: str,
        contract_type: str,
        status: str,
        author: str,
        owner_username: str | None = None,
        content: str,
        source_file_name: str | None = None,
    ) -> WorkbenchContract:
        ...
