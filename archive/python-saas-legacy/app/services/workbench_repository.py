from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.schemas.workbench import StoredChatThread, StoredHistoryLog, StoredReviewRecord, WorkbenchContract, WorkbenchHistoryItem
from app.services.workbench_repository_interface import IWorkbenchRepository


class WorkbenchRepository(IWorkbenchRepository):
    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or ".run/workbench")
        self.reviews_dir = self.base_dir / "reviews"
        self.chats_dir = self.base_dir / "chats"
        self.history_dir = self.base_dir / "history"
        self.contracts_path = self.base_dir / "contracts.json"
        self._lock = Lock()
        self._ensure_storage()

    def list_contracts(self) -> list[WorkbenchContract]:
        payload = self._read_json_file(self.contracts_path, default=[])
        return [WorkbenchContract.model_validate(item) for item in payload]

    def get_contract(self, contract_id: str) -> WorkbenchContract | None:
        for contract in self.list_contracts():
            if contract.id == contract_id:
                return contract
        return None

    def save_contract(self, contract: WorkbenchContract) -> None:
        contracts = self.list_contracts()
        replaced = False
        for index, current in enumerate(contracts):
            if current.id == contract.id:
                contracts[index] = contract
                replaced = True
                break
        if not replaced:
            contracts.append(contract)
        self._write_json_file(self.contracts_path, [item.model_dump(mode="json") for item in contracts])

    def get_review(self, contract_id: str) -> StoredReviewRecord | None:
        path = self.reviews_dir / f"{contract_id}.json"
        payload = self._read_json_file(path, default=None)
        if payload is None:
            return None
        return StoredReviewRecord.model_validate(payload)

    def save_review(self, review: StoredReviewRecord) -> None:
        path = self.reviews_dir / f"{review.contract_id}.json"
        self._write_json_file(path, review.model_dump(mode="json"))

    def get_chat_thread(self, contract_id: str, member_id: int = 0) -> StoredChatThread:
        path = self.chats_dir / f"{self._scope_key(contract_id, member_id)}.json"
        payload = self._read_json_file(path, default=None)
        if payload is None and member_id == 0:
            legacy_path = self.chats_dir / f"{contract_id}.json"
            payload = self._read_json_file(legacy_path, default=None)
        if payload is None:
            return StoredChatThread(contract_id=contract_id)
        return StoredChatThread.model_validate(payload)

    def save_chat_thread(self, thread: StoredChatThread, member_id: int = 0) -> None:
        path = self.chats_dir / f"{self._scope_key(thread.contract_id, member_id)}.json"
        self._write_json_file(path, thread.model_dump(mode="json"))

    def get_history(self, contract_id: str, member_id: int = 0) -> StoredHistoryLog:
        path = self.history_dir / f"{self._scope_key(contract_id, member_id)}.json"
        payload = self._read_json_file(path, default=None)
        if payload is None and member_id == 0:
            legacy_path = self.history_dir / f"{contract_id}.json"
            payload = self._read_json_file(legacy_path, default=None)
        if payload is None:
            return StoredHistoryLog(contract_id=contract_id)
        return StoredHistoryLog.model_validate(payload)

    def save_history(self, history: StoredHistoryLog, member_id: int = 0) -> None:
        path = self.history_dir / f"{self._scope_key(history.contract_id, member_id)}.json"
        self._write_json_file(path, history.model_dump(mode="json"))

    def append_history_item(self, contract_id: str, item: WorkbenchHistoryItem, member_id: int = 0) -> StoredHistoryLog:
        history = self.get_history(contract_id, member_id=member_id)
        history.items.append(item)
        self.save_history(history, member_id=member_id)
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
        now = datetime.now(timezone.utc)
        contract = WorkbenchContract(
            id=f"contract-{uuid4().hex[:12]}",
            title=title,
            type=contract_type,
            status=status,
            updated_at=now,
            author=author,
            owner_username=owner_username,
            content=content,
            created_at=now,
            source_file_name=source_file_name,
        )
        self.save_contract(contract)
        return contract

    def _ensure_storage(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.reviews_dir.mkdir(parents=True, exist_ok=True)
        self.chats_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        if not self.contracts_path.exists():
            self._write_json_file(
                self.contracts_path,
                [contract.model_dump(mode="json") for contract in self._seed_contracts()],
            )

    def _seed_contracts(self) -> list[WorkbenchContract]:
        now = datetime.now(timezone.utc)
        samples = [
            {
                "id": "contract-001",
                "title": "2024年度云服务采购合同",
                "type": "采购合同",
                "status": "reviewing",
                "author": "李明",
                "owner_username": "u1",
                "updated_at": now - timedelta(hours=2),
                "created_at": now - timedelta(days=3),
                "content": "采购合同\n甲方：智联科技有限公司\n乙方：云端计算服务有限公司\n第一条 标的\n乙方应交付云计算资源及相关维护服务。\n第二条 付款方式\n甲方应于合同签订后5日内支付100%合同价款。\n第三条 争议解决\n争议由乙方所在地人民法院管辖。",
            },
            {
                "id": "contract-002",
                "title": "战略合作伙伴框架协议",
                "type": "框架协议",
                "status": "pending",
                "author": "王芳",
                "owner_username": "u2",
                "updated_at": now - timedelta(days=1, hours=4),
                "created_at": now - timedelta(days=5),
                "content": "框架协议\n甲方：甲公司\n乙方：乙公司\n第一条 合作目标\n双方将在市场推广与联合解决方案方面开展合作。",
            },
            {
                "id": "contract-003",
                "title": "办公场地租赁合同",
                "type": "租赁合同",
                "status": "approved",
                "author": "张伟",
                "owner_username": "u3",
                "updated_at": now - timedelta(days=2),
                "created_at": now - timedelta(days=7),
                "content": "租赁合同\n甲方：园区运营公司\n乙方：智联科技有限公司\n第一条 租赁标的\n甲方将办公场地出租给乙方使用。",
            },
            {
                "id": "contract-004",
                "title": "软件开发外包服务协议",
                "type": "服务合同",
                "status": "rejected",
                "author": "赵敏",
                "owner_username": "u4",
                "updated_at": now - timedelta(days=4),
                "created_at": now - timedelta(days=9),
                "content": "服务合同\n甲方：星云软件有限公司\n乙方：乙方开发团队\n第一条 服务内容\n乙方负责完成甲方委托的软件开发工作。",
            },
        ]
        return [WorkbenchContract.model_validate(item) for item in samples]

    def _scope_key(self, contract_id: str, member_id: int) -> str:
        return f"{contract_id}--m{member_id}"

    def _read_json_file(self, path: Path, default):
        with self._lock:
            if not path.exists():
                return default
            return json.loads(path.read_text(encoding="utf-8"))

    def _write_json_file(self, path: Path, payload) -> None:
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
