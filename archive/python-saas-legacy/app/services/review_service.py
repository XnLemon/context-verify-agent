from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import settings
from app.rag.retriever import ContractKnowledgeRetriever
from app.rag.vector_store import is_knowledge_base_ready, load_vector_store
from app.schemas.review import (
    HealthResponse,
    KnowledgeReference,
    ReviewReport,
    ReviewRequest,
    ReviewResponse,
    ReviewSummary,
)
from app.services.classifier import ContractClassifier
from app.services.extractor import ContractExtractor
from app.services.parser import ContractParser
from app.services.rule_engine import RuleEngine

try:
    from app.llm.reviewer import LLMReviewer
except Exception:
    LLMReviewer = None


class ReviewService:
    def __init__(self) -> None:
        self.classifier = ContractClassifier()
        self.extractor = ContractExtractor()
        self.parser = ContractParser()
        self.rule_engine = RuleEngine()
        self._llm_reviewer = None
        self._knowledge_retriever = None

    def health(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            llm_configured=bool(settings.qwen_api_key and LLMReviewer),
            knowledge_base_ready=is_knowledge_base_ready(settings.knowledge_vector_store_dir),
        )

    def review(self, payload: ReviewRequest) -> ReviewResponse:
        document = self.parser.parse_text(payload.contract_text)
        return self._review_document(document=document, contract_type=payload.contract_type, our_side=payload.our_side)

    def review_file(self, file_name: str, content: bytes, contract_type: str | None, our_side: str) -> ReviewResponse:
        document = self.parser.parse_bytes(file_name, content)
        return self._review_document(document=document, contract_type=contract_type, our_side=our_side)

    def parse_file(self, file_name: str, content: bytes):
        return self.parser.parse_bytes(file_name, content)

    def _review_document(self, document, contract_type: str | None, our_side: str) -> ReviewResponse:
        llm_reviewer = self._require_llm_reviewer()
        knowledge_retriever = self._require_knowledge_retriever()

        contract_text = document.raw_text
        detected_contract_type = contract_type or self.classifier.classify(contract_text)
        extracted_fields = self.extractor.extract(contract_text)
        risks = self.rule_engine.check(detected_contract_type, document)
        risks = self._apply_party_context(risks, our_side)
        risks = self._enrich_risks(risks, document, detected_contract_type, llm_reviewer, knowledge_retriever)
        report = self._build_report(risks, detected_contract_type, document.metadata.title or document.metadata.file_name)

        return ReviewResponse(
            summary=ReviewSummary(
                contract_type=detected_contract_type or settings.default_contract_type,
                overall_risk=self._overall_risk(risks),
                risk_count=len(risks),
            ),
            extracted_fields=extracted_fields,
            risks=risks,
            report=report,
        )

    def _overall_risk(self, risks: list) -> str:
        severities = {risk.severity for risk in risks}
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        if "low" in severities:
            return "low"
        return "info"

    def _require_llm_reviewer(self):
        if not settings.qwen_api_key:
            raise RuntimeError("QWEN_API_KEY 未配置，当前交付要求必须启用 LLM。")
        if not LLMReviewer:
            raise RuntimeError("LLM 组件不可用，请检查 langchain/Qwen 相关依赖。")
        if self._llm_reviewer is None:
            try:
                self._llm_reviewer = LLMReviewer()
            except Exception as exc:
                raise RuntimeError(f"LLM 初始化失败：{exc}") from exc
        return self._llm_reviewer

    def _require_knowledge_retriever(self) -> ContractKnowledgeRetriever:
        if self._knowledge_retriever is None:
            try:
                vector_store = load_vector_store(settings.knowledge_vector_store_dir)
            except Exception as exc:
                raise RuntimeError(f"法律知识库加载失败：{exc}") from exc
            self._knowledge_retriever = ContractKnowledgeRetriever(vector_store)
        return self._knowledge_retriever

    def _apply_party_context(self, risks: list, our_side: str) -> list:
        filtered = []
        for risk in risks:
            if risk.rule_id == "JUR_001" and our_side in risk.evidence:
                continue
            filtered.append(risk)
        return filtered

    def _enrich_risks(self, risks: list, document, contract_type: str, llm_reviewer, knowledge_retriever) -> list:
        for risk in risks:
            clause_text = self._find_clause_text(document, risk)
            query = f"{contract_type} {risk.title} {risk.risk_domain or ''} {risk.evidence} {clause_text}"
            retrieved_docs = knowledge_retriever.retrieve_documents_with_rerank(query=query, fetch_k=settings.retrieval_fetch_k, final_k=settings.retrieval_final_k)
            retrieved_contexts = [doc.page_content for doc in retrieved_docs]
            risk.basis_sources = [
                KnowledgeReference(
                    source_title=doc.metadata.get("title") or doc.metadata.get("doc_name") or "未命名知识片段",
                    article_label=doc.metadata.get("article_label"),
                    snippet=doc.page_content[:240],
                    source_path=doc.metadata.get("source_path"),
                )
                for doc in retrieved_docs
            ]
            llm_reviewer.enrich_risk(risk, contract_type, clause_text, retrieved_contexts)
        return risks

    def _build_report(self, risks: list, contract_type: str, document_title: str) -> ReviewReport:
        if risks:
            overview = f"《{document_title}》已按{contract_type}完成校审，共识别出 {len(risks)} 项风险，整体风险等级为 {self._overall_risk(risks)}。"
            key_findings = [f"{risk.title}：{risk.evidence}" for risk in risks[:5]]
            next_actions = [risk.suggestion for risk in risks[:5]]
        else:
            overview = f"《{document_title}》已按{contract_type}完成校审，暂未识别出明确风险。"
            key_findings = []
            next_actions = ["建议结合业务背景继续人工复核关键商务条款。"]

        return ReviewReport(
            generated_at=datetime.now(timezone.utc),
            overview=overview,
            key_findings=key_findings,
            next_actions=next_actions,
        )

    def _find_clause_text(self, document, risk) -> str:
        for chunk in document.clause_chunks:
            if chunk.clause_no == risk.clause_no and chunk.section_title == risk.section_title:
                return chunk.source_text
        return risk.evidence
