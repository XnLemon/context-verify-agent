from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.review import ReviewSummary


ContractStatus = Literal["pending", "reviewing", "approved", "rejected"]
IssueType = Literal["risk", "suggestion", "compliance"]
IssueStatus = Literal["pending", "accepted", "rejected"]
ChatRole = Literal["user", "assistant"]
HistoryEventType = Literal["scan", "issue_decision", "chat", "import", "redraft", "manual_edit", "final_decision"]
FinalDecisionStatus = Literal["approved", "rejected"]


class WorkbenchContract(BaseModel):
    id: str
    title: str
    type: str
    status: ContractStatus
    updated_at: datetime
    author: str
    owner_username: str | None = None
    content: str
    created_at: datetime | None = None
    source_file_name: str | None = None


class WorkbenchContractListItem(BaseModel):
    id: str
    title: str
    type: str
    status: ContractStatus
    updatedAt: str
    author: str
    content: str


class WorkbenchIssue(BaseModel):
    id: str
    type: IssueType
    severity: Literal["high", "medium", "low", "info"]
    message: str
    suggestion: str
    location: str | None = None
    status: IssueStatus = "pending"
    startIndex: int | None = None
    endIndex: int | None = None


class WorkbenchReviewResult(BaseModel):
    summary: ReviewSummary
    reportOverview: str
    keyFindings: list[str] = Field(default_factory=list)
    nextActions: list[str] = Field(default_factory=list)
    issues: list[WorkbenchIssue] = Field(default_factory=list)
    generatedAt: datetime


class WorkbenchChatMessage(BaseModel):
    id: str
    role: ChatRole
    content: str
    timestamp: str
    created_at: datetime | None = None


class WorkbenchHistoryItem(BaseModel):
    id: str
    type: HistoryEventType
    title: str
    description: str
    createdAt: datetime
    metadata: dict[str, str] = Field(default_factory=dict)


class WorkbenchSummaryResponse(BaseModel):
    pendingCount: int
    complianceRate: float
    highRiskCount: int
    averageReviewDurationHours: float
    totalContracts: int


class WorkbenchContractListResponse(BaseModel):
    items: list[WorkbenchContractListItem]
    total: int


class WorkbenchContractDetailResponse(BaseModel):
    contract: WorkbenchContractListItem
    latestReview: WorkbenchReviewResult | None = None
    chatMessages: list[WorkbenchChatMessage] = Field(default_factory=list)


class WorkbenchScanResponse(BaseModel):
    contract: WorkbenchContractListItem
    latestReview: WorkbenchReviewResult
    historyCount: int


class WorkbenchChatRequest(BaseModel):
    message: str | None = Field(default=None, min_length=1)
    messages: list[WorkbenchChatMessage] = Field(default_factory=list)
    contract_type: str | None = None
    our_side: str = "甲方"


class WorkbenchChatResponse(BaseModel):
    intent: str
    toolUsed: str
    assistantMessage: WorkbenchChatMessage
    messages: list[WorkbenchChatMessage]
    latestReview: WorkbenchReviewResult | None = None


class WorkbenchIssueDecisionRequest(BaseModel):
    status: IssueStatus
    auto_redraft: bool = True


class WorkbenchFinalDecisionRequest(BaseModel):
    status: FinalDecisionStatus
    comment: str | None = None


class WorkbenchContractUpdateRequest(BaseModel):
    content: str = Field(min_length=1)


class WorkbenchContractUpdateResponse(BaseModel):
    contract: WorkbenchContractListItem


class WorkbenchImportResponse(BaseModel):
    contract: WorkbenchContractListItem


class WorkbenchFinalDecisionResponse(BaseModel):
    contract: WorkbenchContractListItem
    historyCount: int


class StoredReviewRecord(BaseModel):
    contract_id: str
    summary: ReviewSummary
    report_overview: str
    key_findings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    issues: list[WorkbenchIssue] = Field(default_factory=list)
    generated_at: datetime


class StoredChatThread(BaseModel):
    contract_id: str
    messages: list[WorkbenchChatMessage] = Field(default_factory=list)


class StoredHistoryLog(BaseModel):
    contract_id: str
    items: list[WorkbenchHistoryItem] = Field(default_factory=list)


class WorkbenchRedraftRequest(BaseModel):
    our_side: str = "甲方"


class WorkbenchRedraftResponse(BaseModel):
    contract: WorkbenchContractListItem
    latestReview: WorkbenchReviewResult
    acceptedIssueCount: int
