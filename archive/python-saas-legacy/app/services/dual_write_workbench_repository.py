from __future__ import annotations

from app.schemas.workbench import StoredChatThread, StoredHistoryLog, StoredReviewRecord, WorkbenchContract, WorkbenchHistoryItem
from app.services.workbench_repository import WorkbenchRepository
from app.services.workbench_repository_interface import IWorkbenchRepository


class DualWriteWorkbenchRepository(IWorkbenchRepository):
    def __init__(self, json_repo: WorkbenchRepository, pg_repo: IWorkbenchRepository | None) -> None:
        self.json_repo = json_repo
        self.pg_repo = pg_repo

    def list_contracts(self) -> list[WorkbenchContract]:
        primary = self.json_repo.list_contracts()
        if primary:
            return primary
        if self.pg_repo is None:
            return []
        return self.pg_repo.list_contracts()

    def get_contract(self, contract_id: str) -> WorkbenchContract | None:
        contract = self.json_repo.get_contract(contract_id)
        if contract is not None:
            return contract
        if self.pg_repo is None:
            return None
        return self.pg_repo.get_contract(contract_id)

    def save_contract(self, contract: WorkbenchContract) -> None:
        self.json_repo.save_contract(contract)
        self._mirror_call(lambda repo: repo.save_contract(contract))

    def get_review(self, contract_id: str) -> StoredReviewRecord | None:
        review = self.json_repo.get_review(contract_id)
        if review is not None:
            return review
        if self.pg_repo is None:
            return None
        return self.pg_repo.get_review(contract_id)

    def save_review(self, review: StoredReviewRecord) -> None:
        self.json_repo.save_review(review)
        self._mirror_call(lambda repo: repo.save_review(review))

    def get_chat_thread(self, contract_id: str, member_id: int = 0) -> StoredChatThread:
        thread = self.json_repo.get_chat_thread(contract_id, member_id=member_id)
        if thread.messages:
            return thread
        if self.pg_repo is None:
            return thread
        return self.pg_repo.get_chat_thread(contract_id, member_id=member_id)

    def save_chat_thread(self, thread: StoredChatThread, member_id: int = 0) -> None:
        self.json_repo.save_chat_thread(thread, member_id=member_id)
        self._mirror_call(lambda repo: repo.save_chat_thread(thread, member_id=member_id))

    def get_history(self, contract_id: str, member_id: int = 0) -> StoredHistoryLog:
        history = self.json_repo.get_history(contract_id, member_id=member_id)
        if history.items:
            return history
        if self.pg_repo is None:
            return history
        return self.pg_repo.get_history(contract_id, member_id=member_id)

    def save_history(self, history: StoredHistoryLog, member_id: int = 0) -> None:
        self.json_repo.save_history(history, member_id=member_id)
        self._mirror_call(lambda repo: repo.save_history(history, member_id=member_id))

    def append_history_item(self, contract_id: str, item: WorkbenchHistoryItem, member_id: int = 0) -> StoredHistoryLog:
        history = self.json_repo.append_history_item(contract_id, item, member_id=member_id)
        self._mirror_call(lambda repo: repo.append_history_item(contract_id, item, member_id=member_id))
        return history

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
        contract = self.json_repo.create_contract(
            title=title,
            contract_type=contract_type,
            status=status,
            author=author,
            owner_username=owner_username,
            content=content,
            source_file_name=source_file_name,
        )
        self._mirror_call(lambda repo: repo.save_contract(contract))
        return contract

    def _mirror_call(self, callback) -> None:
        if self.pg_repo is None:
            return
        try:
            callback(self.pg_repo)
        except Exception as exc:
            raise RuntimeError(f"Dual-write to PostgreSQL failed: {exc}") from exc
