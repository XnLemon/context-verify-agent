from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from threading import Lock, RLock
from uuid import uuid4

from app.core.config import settings
from app.llm.editor import ContractEditor
from app.schemas.auth import MemberPublic
from app.schemas.chat import ChatRequest as CoreChatRequest
from app.schemas.review import ReviewRequest, ReviewResponse, RiskItem
from app.schemas.workbench import (
    StoredChatThread,
    StoredReviewRecord,
    WorkbenchChatMessage,
    WorkbenchChatRequest,
    WorkbenchChatResponse,
    WorkbenchContract,
    WorkbenchContractDetailResponse,
    WorkbenchContractListItem,
    WorkbenchContractListResponse,
    WorkbenchContractUpdateResponse,
    WorkbenchFinalDecisionResponse,
    WorkbenchHistoryItem,
    WorkbenchImportResponse,
    WorkbenchIssue,
    WorkbenchIssueDecisionRequest,
    WorkbenchRedraftResponse,
    WorkbenchReviewResult,
    WorkbenchScanResponse,
    WorkbenchSummaryResponse,
)
from app.services.chat_service import ChatService
from app.services.review_service import ReviewService
from app.services.workbench_repository_factory import build_workbench_repository
from app.services.workbench_repository_interface import IWorkbenchRepository


class WorkbenchService:
    def __init__(
        self,
        repository: IWorkbenchRepository | None = None,
        review_service: ReviewService | None = None,
        chat_service: ChatService | None = None,
    ) -> None:
        self.repository = repository or build_workbench_repository()
        self.review_service = review_service or ReviewService()
        self.chat_service = chat_service or ChatService()
        self._contract_editor: ContractEditor | None = None
        self._contract_locks: dict[str, RLock] = {}
        self._contract_locks_guard = Lock()

    def get_summary(self, current_member: MemberPublic | None = None) -> WorkbenchSummaryResponse:
        contracts = self._filter_visible_contracts(self.repository.list_contracts(), current_member)
        reviews = [self.repository.get_review(contract.id) for contract in contracts]
        available_reviews = [review for review in reviews if review is not None]
        pending_count = sum(1 for contract in contracts if contract.status == "pending")
        high_risk_count = sum(
            1
            for review in available_reviews
            for issue in review.issues
            if issue.severity == "high" and issue.status == "pending"
        )
        compliance_rate = 100.0
        if available_reviews:
            compliant_count = sum(1 for review in available_reviews if review.summary.overall_risk in {"low", "info"})
            compliance_rate = round(compliant_count / len(available_reviews) * 100, 1)

        durations: list[float] = []
        for contract in contracts:
            review = self.repository.get_review(contract.id)
            if review is None:
                continue
            durations.append((review.generated_at - contract.created_at).total_seconds() / 3600)
        average_duration = round(mean(durations), 1) if durations else 0.0

        return WorkbenchSummaryResponse(
            pendingCount=pending_count,
            complianceRate=compliance_rate,
            highRiskCount=high_risk_count,
            averageReviewDurationHours=average_duration,
            totalContracts=len(contracts),
        )

    def list_contracts(
        self,
        status: str | None = None,
        search: str | None = None,
        current_member: MemberPublic | None = None,
    ) -> WorkbenchContractListResponse:
        contracts = self._filter_visible_contracts(self.repository.list_contracts(), current_member)
        filtered: list[WorkbenchContractListItem] = []
        keyword = (search or "").strip().lower()
        for contract in contracts:
            if status and contract.status != status:
                continue
            if keyword and keyword not in f"{contract.title} {contract.type} {contract.author} {contract.content}".lower():
                continue
            filtered.append(self._to_list_item(contract))
        filtered.sort(key=lambda item: item.updatedAt, reverse=True)
        return WorkbenchContractListResponse(items=filtered, total=len(filtered))

    def get_contract_detail(
        self,
        contract_id: str,
        current_member: MemberPublic | None = None,
    ) -> WorkbenchContractDetailResponse:
        contract = self._require_contract(contract_id, current_member)
        review = self.repository.get_review(contract_id)
        chat_thread = self.repository.get_chat_thread(contract_id)
        return WorkbenchContractDetailResponse(
            contract=self._to_list_item(contract),
            latestReview=self._to_review_result(review) if review else None,
            chatMessages=chat_thread.messages,
        )

    def scan_contract(
        self,
        contract_id: str,
        contract_type: str | None = None,
        our_side: str = "甲方",
        current_member: MemberPublic | None = None,
    ) -> WorkbenchScanResponse:
        contract = self._require_contract(contract_id, current_member)
        review_response = self.review_service.review(
            ReviewRequest(
                contract_text=contract.content,
                contract_type=contract_type or contract.type,
                our_side=our_side,
            )
        )
        stored_review = self._build_stored_review(contract_id, review_response, previous_review=None)
        self.repository.save_review(stored_review)

        contract.type = review_response.summary.contract_type
        contract.status = self._derive_contract_status(stored_review)
        contract.updated_at = datetime.now(timezone.utc)
        self.repository.save_contract(contract)

        history = self.repository.append_history_item(
            contract_id,
            self._history_item(
                event_type="scan",
                title="完成合同扫描",
                description=f"识别到 {stored_review.summary.risk_count} 项风险，整体等级 {stored_review.summary.overall_risk}。",
                metadata={"overall_risk": stored_review.summary.overall_risk},
            ),
        )
        return WorkbenchScanResponse(
            contract=self._to_list_item(contract),
            latestReview=self._to_review_result(stored_review),
            historyCount=len(history.items),
        )

    def chat_contract(
        self,
        contract_id: str,
        payload: WorkbenchChatRequest,
        current_member: MemberPublic | None = None,
    ) -> WorkbenchChatResponse:
        contract = self._require_contract(contract_id, current_member)
        existing_thread = self.repository.get_chat_thread(contract_id)
        messages = list(payload.messages) if payload.messages else list(existing_thread.messages)

        if payload.message:
            messages.append(self._chat_message(role="user", content=payload.message))

        if not messages:
            raise ValueError("至少需要一条用户消息。")

        chat_response = self.chat_service.chat(
            CoreChatRequest(
                messages=[{"role": message.role, "content": message.content} for message in messages],
                contract_text=contract.content,
                contract_type=payload.contract_type or contract.type,
                our_side=payload.our_side,
            )
        )
        assistant_message = self._chat_message(role="assistant", content=chat_response.answer)
        messages.append(assistant_message)
        self.repository.save_chat_thread(StoredChatThread(contract_id=contract_id, messages=messages))

        latest_review = None
        if chat_response.review_result is not None:
            previous_review = self.repository.get_review(contract_id)
            stored_review = self._build_stored_review(contract_id, chat_response.review_result, previous_review)
            self.repository.save_review(stored_review)
            latest_review = self._to_review_result(stored_review)
            contract.status = self._derive_contract_status(stored_review)
            contract.updated_at = datetime.now(timezone.utc)
            self.repository.save_contract(contract)
            self.repository.append_history_item(
                contract_id,
                self._history_item(
                    event_type="scan",
                    title="对话触发复审",
                    description=f"AI 对话触发复审，识别到 {stored_review.summary.risk_count} 项风险。",
                    metadata={"tool_used": chat_response.tool_used},
                ),
            )

        self.repository.append_history_item(
            contract_id,
            self._history_item(
                event_type="chat",
                title="新增 AI 对话",
                description=messages[-2].content if len(messages) >= 2 else assistant_message.content,
                metadata={"tool_used": chat_response.tool_used, "intent": chat_response.intent},
            ),
        )

        return WorkbenchChatResponse(
            intent=chat_response.intent,
            toolUsed=chat_response.tool_used,
            assistantMessage=assistant_message,
            messages=messages,
            latestReview=latest_review,
        )

    def decide_issue(
        self,
        contract_id: str,
        issue_id: str,
        payload: WorkbenchIssueDecisionRequest,
        current_member: MemberPublic | None = None,
    ) -> WorkbenchReviewResult:
        with self._get_contract_lock(contract_id):
            contract = self._require_contract(contract_id, current_member)
            review = self.repository.get_review(contract_id)
            if review is None:
                raise KeyError(f"Contract review not found: {contract_id}")

            updated = False
            for issue in review.issues:
                if issue.id == issue_id:
                    issue.status = payload.status
                    updated = True
                    break
            if not updated:
                raise KeyError(f"Issue not found: {issue_id}")

            self.repository.save_review(review)
            contract.status = self._derive_contract_status(review)
            contract.updated_at = datetime.now(timezone.utc)
            self.repository.save_contract(contract)
            self.repository.append_history_item(
                contract_id,
                self._history_item(
                    event_type="issue_decision",
                    title="更新风险处理状态",
                    description=f"问题 {issue_id} 已标记为 {payload.status}。",
                    metadata={"issue_id": issue_id, "status": payload.status},
                ),
            )

            if payload.auto_redraft and payload.status == "accepted":
                self._try_auto_redraft(contract_id=contract_id, current_member=current_member)

            latest_review = self.repository.get_review(contract_id)
            if latest_review is None:
                raise KeyError(f"Contract review not found: {contract_id}")
            return self._to_review_result(latest_review)

    def redraft_contract(
        self,
        contract_id: str,
        our_side: str = "甲方",
        current_member: MemberPublic | None = None,
    ) -> WorkbenchRedraftResponse:
        with self._get_contract_lock(contract_id):
            contract = self._require_contract(contract_id, current_member)
            review = self.repository.get_review(contract_id)
            if review is None:
                raise KeyError(f"Contract review not found: {contract_id}")

            accepted_issues = [issue for issue in review.issues if issue.status == "accepted"]
            if not accepted_issues:
                raise ValueError("当前没有已采纳的问题，无法生成修订稿。")

            editor = self._require_contract_editor()
            revised_text = editor.redraft_contract(
                contract_text=contract.content,
                contract_type=contract.type,
                our_side=our_side,
                accepted_issues=[
                    {
                        "message": issue.message,
                        "suggestion": issue.suggestion,
                        "location": issue.location or "",
                    }
                    for issue in accepted_issues
                ],
            )

            contract.content = revised_text
            contract.updated_at = datetime.now(timezone.utc)
            self.repository.save_contract(contract)
            self.repository.append_history_item(
                contract_id,
                self._history_item(
                    event_type="redraft",
                    title="生成合同修订稿",
                    description=f"已基于 {len(accepted_issues)} 条采纳建议生成合同修订稿。",
                    metadata={"accepted_issue_count": str(len(accepted_issues))},
                ),
            )

            return WorkbenchRedraftResponse(
                contract=self._to_list_item(contract),
                latestReview=self._to_review_result(review),
                acceptedIssueCount=len(accepted_issues),
            )

    def get_history(self, contract_id: str, current_member: MemberPublic | None = None) -> list[WorkbenchHistoryItem]:
        self._require_contract(contract_id, current_member)
        history = self.repository.get_history(contract_id)
        return sorted(history.items, key=lambda item: item.createdAt, reverse=True)

    def update_contract_content(
        self,
        contract_id: str,
        content: str,
        current_member: MemberPublic | None = None,
    ) -> WorkbenchContractUpdateResponse:
        if not content.strip():
            raise ValueError("合同正文不能为空。")

        with self._get_contract_lock(contract_id):
            contract = self._require_contract(contract_id, current_member)
            contract.content = content
            contract.status = "pending"
            contract.updated_at = datetime.now(timezone.utc)
            self.repository.save_contract(contract)
            self.repository.append_history_item(
                contract_id,
                self._history_item(
                    event_type="manual_edit",
                    title="手动编辑合同",
                    description="已手动更新合同正文，建议重新执行扫描。",
                    metadata={"content_length": str(len(content))},
                ),
            )
            return WorkbenchContractUpdateResponse(contract=self._to_list_item(contract))

    def finalize_contract(
        self,
        *,
        contract_id: str,
        status: str,
        operator_name: str,
        comment: str | None = None,
        current_member: MemberPublic | None = None,
    ) -> WorkbenchFinalDecisionResponse:
        if status not in {"approved", "rejected"}:
            raise ValueError("最终审批状态必须为 approved 或 rejected。")

        with self._get_contract_lock(contract_id):
            contract = self._require_contract(contract_id, current_member)
            contract.status = status
            contract.updated_at = datetime.now(timezone.utc)
            self.repository.save_contract(contract)
            history = self.repository.append_history_item(
                contract_id,
                self._history_item(
                    event_type="final_decision",
                    title="完成最终审批",
                    description=(
                        f"{operator_name} 将合同标记为 {'通过' if status == 'approved' else '驳回'}。"
                        f"{' 备注：' + comment.strip() if comment and comment.strip() else ''}"
                    ),
                    metadata={
                        "status": status,
                        "operator": operator_name,
                    },
                ),
            )
            return WorkbenchFinalDecisionResponse(
                contract=self._to_list_item(contract),
                historyCount=len(history.items),
            )

    def import_contract(
        self,
        *,
        file_name: str,
        content: bytes,
        contract_type: str | None = None,
        author: str = "系统导入",
        owner_username: str | None = None,
    ) -> WorkbenchImportResponse:
        parsed = self.review_service.parse_file(file_name, content)
        contract = self.repository.create_contract(
            title=parsed.metadata.title or Path(file_name).stem,
            contract_type=contract_type or parsed.metadata.contract_type_hint or settings.default_contract_type,
            status="pending",
            author=author,
            owner_username=owner_username,
            content=parsed.raw_text,
            source_file_name=file_name,
        )
        self.repository.append_history_item(
            contract.id,
            self._history_item(
                event_type="import",
                title="导入合同",
                description=f"已从文件 {file_name} 导入合同。",
                metadata={"file_name": file_name},
            ),
        )
        return WorkbenchImportResponse(contract=self._to_list_item(contract))

    def _try_auto_redraft(
        self,
        *,
        contract_id: str,
        current_member: MemberPublic | None = None,
    ) -> None:
        try:
            self.redraft_contract(contract_id=contract_id, our_side="甲方", current_member=current_member)
        except Exception as exc:
            self.repository.append_history_item(
                contract_id,
                self._history_item(
                    event_type="redraft",
                    title="自动修订失败",
                    description=f"自动修订未完成：{exc}",
                    metadata={"status": "failed"},
                ),
            )

    def _require_contract_editor(self) -> ContractEditor:
        if not settings.qwen_api_key:
            raise RuntimeError("QWEN_API_KEY 未配置，无法生成合同修订稿。")
        if self._contract_editor is None:
            try:
                self._contract_editor = ContractEditor()
            except Exception as exc:
                raise RuntimeError(f"合同修订模型初始化失败：{exc}") from exc
        return self._contract_editor

    def _get_contract_lock(self, contract_id: str) -> RLock:
        with self._contract_locks_guard:
            lock = self._contract_locks.get(contract_id)
            if lock is None:
                lock = RLock()
                self._contract_locks[contract_id] = lock
            return lock

    def _require_contract(
        self,
        contract_id: str,
        current_member: MemberPublic | None = None,
    ) -> WorkbenchContract:
        contract = self.repository.get_contract(contract_id)
        if contract is None:
            raise KeyError(f"Contract not found: {contract_id}")
        if current_member and self._is_owner_restricted_member(current_member):
            if contract.owner_username != current_member.username:
                raise KeyError(f"Contract not found: {contract_id}")
        return contract

    def _filter_visible_contracts(
        self,
        contracts: list[WorkbenchContract],
        current_member: MemberPublic | None = None,
    ) -> list[WorkbenchContract]:
        if not current_member or not self._is_owner_restricted_member(current_member):
            return contracts
        return [contract for contract in contracts if contract.owner_username == current_member.username]

    def _is_owner_restricted_member(self, member: MemberPublic) -> bool:
        return member.role == "employee" and member.member_type != "legal"

    def _build_stored_review(
        self,
        contract_id: str,
        review_response: ReviewResponse,
        previous_review: StoredReviewRecord | None,
    ) -> StoredReviewRecord:
        previous_statuses = {}
        if previous_review is not None:
            previous_statuses = {issue.id: issue.status for issue in previous_review.issues}

        issues: list[WorkbenchIssue] = []
        for index, risk in enumerate(review_response.risks, start=1):
            issue = self._map_issue(risk, index)
            if issue.id in previous_statuses:
                issue.status = previous_statuses[issue.id]
            issues.append(issue)

        return StoredReviewRecord(
            contract_id=contract_id,
            summary=review_response.summary,
            report_overview=review_response.report.overview,
            key_findings=review_response.report.key_findings,
            next_actions=review_response.report.next_actions,
            issues=issues,
            generated_at=review_response.report.generated_at,
        )

    def _map_issue(self, risk: RiskItem, index: int) -> WorkbenchIssue:
        location_parts = [part for part in (risk.clause_no, risk.section_title) if part]
        start_offset = risk.start_offset if risk.start_offset is not None else index
        issue_type = self._map_issue_type(risk)
        return WorkbenchIssue(
            id=f"{risk.rule_id}-{start_offset}-{index}",
            type=issue_type,
            severity=risk.severity,
            message=risk.title,
            suggestion=risk.suggestion,
            location=" | ".join(location_parts) if location_parts else None,
            status="pending",
            startIndex=risk.start_offset,
            endIndex=risk.end_offset,
        )

    def _map_issue_type(self, risk: RiskItem) -> str:
        domain = risk.risk_domain or ""
        if any(keyword in domain for keyword in ("主体", "合规", "资质")):
            return "compliance"
        if risk.severity == "low":
            return "suggestion"
        return "risk"

    def _derive_contract_status(self, review: StoredReviewRecord) -> str:
        pending_issues = [issue for issue in review.issues if issue.status == "pending"]
        return "reviewing" if pending_issues else "approved"

    def _to_list_item(self, contract: WorkbenchContract) -> WorkbenchContractListItem:
        return WorkbenchContractListItem(
            id=contract.id,
            title=contract.title,
            type=contract.type,
            status=contract.status,
            updatedAt=contract.updated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            author=contract.author,
            content=contract.content,
        )

    def _to_review_result(self, review: StoredReviewRecord) -> WorkbenchReviewResult:
        return WorkbenchReviewResult(
            summary=review.summary,
            reportOverview=review.report_overview,
            keyFindings=review.key_findings,
            nextActions=review.next_actions,
            issues=review.issues,
            generatedAt=review.generated_at,
        )

    def _chat_message(self, role: str, content: str) -> WorkbenchChatMessage:
        created_at = datetime.now(timezone.utc)
        return WorkbenchChatMessage(
            id=f"msg-{uuid4().hex[:12]}",
            role=role,
            content=content,
            timestamp=created_at.astimezone(timezone.utc).strftime("%H:%M"),
            created_at=created_at,
        )

    def _history_item(
        self,
        *,
        event_type: str,
        title: str,
        description: str,
        metadata: dict[str, str] | None = None,
    ) -> WorkbenchHistoryItem:
        return WorkbenchHistoryItem(
            id=f"history-{uuid4().hex[:12]}",
            type=event_type,
            title=title,
            description=description,
            createdAt=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
