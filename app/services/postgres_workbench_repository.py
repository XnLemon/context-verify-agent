from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.db.init_db import ensure_postgres_schema
from app.db.models import (
    ChatMessageModel,
    ChatThreadModel,
    ContractModel,
    HistoryLogModel,
    ReviewIssueModel,
    ReviewRecordModel,
)
from app.db.session import session_scope
from app.schemas.workbench import (
    StoredChatThread,
    StoredHistoryLog,
    StoredReviewRecord,
    WorkbenchChatMessage,
    WorkbenchContract,
    WorkbenchHistoryItem,
    WorkbenchIssue,
)
from app.services.workbench_repository_interface import IWorkbenchRepository


class PostgresWorkbenchRepository(IWorkbenchRepository):
    def __init__(self) -> None:
        ensure_postgres_schema()

    def list_contracts(self) -> list[WorkbenchContract]:
        with session_scope() as session:
            rows = session.scalars(select(ContractModel)).all()
            return [self._to_contract(row) for row in rows]

    def get_contract(self, contract_id: str) -> WorkbenchContract | None:
        with session_scope() as session:
            row = session.get(ContractModel, contract_id)
            return self._to_contract(row) if row else None

    def save_contract(self, contract: WorkbenchContract) -> None:
        with session_scope() as session:
            row = session.get(ContractModel, contract.id)
            if row is None:
                row = ContractModel(id=contract.id)
                session.add(row)
            row.title = contract.title
            row.type = contract.type
            row.status = contract.status
            row.author = contract.author
            row.owner_username = contract.owner_username
            row.content = contract.content
            row.source_file_name = contract.source_file_name
            row.created_at = contract.created_at or datetime.now(timezone.utc)
            row.updated_at = contract.updated_at

    def get_review(self, contract_id: str) -> StoredReviewRecord | None:
        with session_scope() as session:
            row = session.scalar(
                select(ReviewRecordModel).where(ReviewRecordModel.contract_id == contract_id)
            )
            if row is None:
                return None
            issues = [self._to_issue(item) for item in row.issues]
            return StoredReviewRecord(
                contract_id=row.contract_id,
                summary=row.summary,
                report_overview=row.report_overview,
                key_findings=list(row.key_findings or []),
                next_actions=list(row.next_actions or []),
                issues=issues,
                generated_at=row.generated_at,
            )

    def save_review(self, review: StoredReviewRecord) -> None:
        with session_scope() as session:
            row = session.scalar(
                select(ReviewRecordModel).where(ReviewRecordModel.contract_id == review.contract_id)
            )
            if row is None:
                row = ReviewRecordModel(
                    contract_id=review.contract_id,
                    summary=review.summary.model_dump(mode="json"),
                    report_overview=review.report_overview,
                    key_findings=list(review.key_findings),
                    next_actions=list(review.next_actions),
                    generated_at=review.generated_at,
                )
                session.add(row)
                session.flush()
            else:
                row.summary = review.summary.model_dump(mode="json")
                row.report_overview = review.report_overview
                row.key_findings = list(review.key_findings)
                row.next_actions = list(review.next_actions)
                row.generated_at = review.generated_at

            session.execute(delete(ReviewIssueModel).where(ReviewIssueModel.review_id == row.id))
            for issue in review.issues:
                session.add(
                    ReviewIssueModel(
                        review_id=row.id,
                        contract_id=review.contract_id,
                        issue_id=issue.id,
                        type=issue.type,
                        severity=issue.severity,
                        message=issue.message,
                        suggestion=issue.suggestion,
                        location=issue.location,
                        status=issue.status,
                        start_index=issue.startIndex,
                        end_index=issue.endIndex,
                    )
                )

    def get_chat_thread(self, contract_id: str, member_id: int = 0) -> StoredChatThread:
        with session_scope() as session:
            thread = session.scalar(
                select(ChatThreadModel).where(
                    ChatThreadModel.contract_id == contract_id,
                    ChatThreadModel.member_id == member_id,
                )
            )
            if thread is None:
                return StoredChatThread(contract_id=contract_id)

            messages = [self._to_chat_message(item) for item in sorted(thread.messages, key=lambda msg: msg.id)]
            return StoredChatThread(contract_id=contract_id, messages=messages)

    def save_chat_thread(self, thread: StoredChatThread, member_id: int = 0) -> None:
        with session_scope() as session:
            db_thread = session.scalar(
                select(ChatThreadModel).where(
                    ChatThreadModel.contract_id == thread.contract_id,
                    ChatThreadModel.member_id == member_id,
                )
            )
            now = datetime.now(timezone.utc)
            if db_thread is None:
                db_thread = ChatThreadModel(
                    contract_id=thread.contract_id,
                    member_id=member_id,
                    created_at=now,
                    updated_at=now,
                )
                session.add(db_thread)
                session.flush()
            else:
                db_thread.updated_at = now

            session.execute(delete(ChatMessageModel).where(ChatMessageModel.thread_id == db_thread.id))
            for message in thread.messages:
                session.add(
                    ChatMessageModel(
                        thread_id=db_thread.id,
                        contract_id=thread.contract_id,
                        msg_id=message.id,
                        role=message.role,
                        content=message.content,
                        timestamp=message.timestamp,
                        created_at=message.created_at,
                    )
                )

    def get_history(self, contract_id: str, member_id: int = 0) -> StoredHistoryLog:
        with session_scope() as session:
            rows = session.scalars(
                select(HistoryLogModel).where(
                    HistoryLogModel.contract_id == contract_id,
                    HistoryLogModel.member_id == member_id,
                )
            ).all()
            items = [self._to_history_item(row) for row in rows]
            return StoredHistoryLog(contract_id=contract_id, items=items)

    def save_history(self, history: StoredHistoryLog, member_id: int = 0) -> None:
        with session_scope() as session:
            session.execute(
                delete(HistoryLogModel).where(
                    HistoryLogModel.contract_id == history.contract_id,
                    HistoryLogModel.member_id == member_id,
                )
            )
            for item in history.items:
                session.add(
                    HistoryLogModel(
                        contract_id=history.contract_id,
                        member_id=member_id,
                        event_id=item.id,
                        type=item.type,
                        title=item.title,
                        description=item.description,
                        created_at=item.createdAt,
                        metadata_json=item.metadata,
                    )
                )

    def append_history_item(self, contract_id: str, item: WorkbenchHistoryItem, member_id: int = 0) -> StoredHistoryLog:
        with session_scope() as session:
            session.add(
                HistoryLogModel(
                    contract_id=contract_id,
                    member_id=member_id,
                    event_id=item.id,
                    type=item.type,
                    title=item.title,
                    description=item.description,
                    created_at=item.createdAt,
                    metadata_json=item.metadata,
                )
            )
            rows = session.scalars(
                select(HistoryLogModel).where(
                    HistoryLogModel.contract_id == contract_id,
                    HistoryLogModel.member_id == member_id,
                )
            ).all()
            items = [self._to_history_item(row) for row in rows]
            return StoredHistoryLog(contract_id=contract_id, items=items)

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
        from uuid import uuid4

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

    def _to_contract(self, row: ContractModel) -> WorkbenchContract:
        return WorkbenchContract(
            id=row.id,
            title=row.title,
            type=row.type,
            status=row.status,
            updated_at=row.updated_at,
            author=row.author,
            owner_username=row.owner_username,
            content=row.content,
            created_at=row.created_at,
            source_file_name=row.source_file_name,
        )

    def _to_issue(self, row: ReviewIssueModel) -> WorkbenchIssue:
        return WorkbenchIssue(
            id=row.issue_id,
            type=row.type,
            severity=row.severity,
            message=row.message,
            suggestion=row.suggestion,
            location=row.location,
            status=row.status,
            startIndex=row.start_index,
            endIndex=row.end_index,
        )

    def _to_chat_message(self, row: ChatMessageModel) -> WorkbenchChatMessage:
        return WorkbenchChatMessage(
            id=row.msg_id,
            role=row.role,
            content=row.content,
            timestamp=row.timestamp,
            created_at=row.created_at,
        )

    def _to_history_item(self, row: HistoryLogModel) -> WorkbenchHistoryItem:
        return WorkbenchHistoryItem(
            id=row.event_id,
            type=row.type,
            title=row.title,
            description=row.description,
            createdAt=row.created_at,
            metadata=dict(row.metadata_json or {}),
        )
