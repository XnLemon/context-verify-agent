from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


Severity = Literal["high", "medium", "low", "info"]


class HealthResponse(BaseModel):
    status: str
    llm_configured: bool
    knowledge_base_ready: bool


class ReviewRequest(BaseModel):
    contract_text: str = Field(..., min_length=1, description="合同全文文本")
    contract_type: str | None = Field(default=None, description="合同类型，例如采购合同")
    our_side: str = Field(default="甲方", description="我方角色，例如甲方/乙方")


class ExtractedFields(BaseModel):
    contract_name: str | None = None
    party_a: str | None = None
    party_b: str | None = None
    amount: str | None = None
    dispute_clause: str | None = None


class KnowledgeReference(BaseModel):
    source_title: str
    article_label: str | None = None
    snippet: str
    source_path: str | None = None


class RiskItem(BaseModel):
    rule_id: str
    title: str
    severity: Severity
    description: str
    evidence: str
    suggestion: str
    risk_domain: str | None = None
    ai_explanation: str | None = None
    basis_sources: list[KnowledgeReference] = Field(default_factory=list)
    clause_no: str | None = None
    section_title: str | None = None
    page_no: int | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    chunk_level: str | None = None

    @model_validator(mode="after")
    def validate_offsets(self):
        if self.start_offset is not None and self.end_offset is not None and self.start_offset > self.end_offset:
            raise ValueError(f"start_offset ({self.start_offset}) must not exceed end_offset ({self.end_offset})")
        return self


class ReviewSummary(BaseModel):
    contract_type: str
    overall_risk: Severity
    risk_count: int


class ReviewReport(BaseModel):
    generated_at: datetime
    overview: str
    key_findings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    summary: ReviewSummary
    extracted_fields: ExtractedFields
    risks: list[RiskItem]
    report: ReviewReport
