from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.llm.reviewer import LLMReviewer
from app.multi_agent.protocol import AgentFinding, AgentOutput, AgentStatus
from app.rag.retriever import ContractKnowledgeRetriever
from app.rag.vector_store import load_vector_store
from app.services.classifier import ContractClassifier
from app.services.extractor import ContractExtractor
from app.services.parser import ContractParser
from app.services.rule_engine import RuleEngine


# ---------------------------------------------------------------------------
# Agent 1: Parser — parse contract text into structured clauses
# ---------------------------------------------------------------------------

def parser_agent(ctx: dict[str, Any]) -> AgentOutput:
    contract_text: str = ctx.get("contract_text", "")
    contract_type: str | None = ctx.get("contract_type")
    our_side: str = ctx.get("our_side", "甲方")

    parser = ContractParser()
    classifier = ContractClassifier()
    extractor = ContractExtractor()

    document = parser.parse_text(contract_text)
    detected_type = contract_type or classifier.classify(contract_text)
    extracted = extractor.extract(contract_text)

    clauses = []
    for chunk in document.clause_chunks:
        clauses.append({
            "clause_no": chunk.clause_no,
            "section_title": chunk.section_title,
            "text": chunk.source_text[:500],
            "chunk_id": chunk.chunk_id,
        })

    return AgentOutput(
        agent_id="parser",
        status=AgentStatus.COMPLETED,
        input_summary=f"解析合同，共 {len(clauses)} 个条款",
        structured_data={
            "parsed_clauses": clauses,
            "detected_contract_type": detected_type,
            "extracted_fields": extracted.model_dump(mode="json") if extracted else {},
            "our_side": our_side,
        },
        token_used=0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Agent 2: Risk Checker — run rule engine + LLM enrichment
# ---------------------------------------------------------------------------

def _find_clause_text(clauses: list[dict], clause_no: str) -> str:
    for c in clauses:
        if c["clause_no"] == clause_no:
            return c["text"]
    return ""


def risk_checker_agent(ctx: dict[str, Any]) -> AgentOutput:
    clauses: list[dict] = ctx.get("parsed_clauses", [])
    contract_type: str = ctx.get("detected_contract_type", settings.default_contract_type)
    our_side: str = ctx.get("our_side", "甲方")

    rule_engine = RuleEngine()
    contract_text = ctx.get("contract_text", "")

    from app.schemas.document import ClauseChunk, DocumentMetadata, ParsedDocument
    dummy_doc = ParsedDocument(
        raw_text=contract_text,
        metadata=DocumentMetadata(file_name="contract.txt"),
        spans=[],
        clause_chunks=[
            ClauseChunk(
                chunk_id=c["chunk_id"],
                clause_no=c["clause_no"],
                section_title=c["section_title"],
                source_text=c["text"],
            )
            for c in clauses
        ],
    )

    risks = rule_engine.check(contract_type, dummy_doc)
    risks = _apply_party_context(risks, our_side)

    llm_reviewer = LLMReviewer()
    knowledge_retriever = None
    try:
        vector_store = load_vector_store(settings.knowledge_vector_store_dir)
        knowledge_retriever = ContractKnowledgeRetriever(vector_store)
    except Exception:
        pass

    findings = []
    for risk in risks:
        clause_text = _find_clause_text(clauses, risk.clause_no)
        retrieved_contexts = []
        if knowledge_retriever:
            query = f"{contract_type} {risk.title} {risk.evidence}"
            docs = knowledge_retriever.retrieve_documents_with_rerank(
                query=query, fetch_k=settings.retrieval_fetch_k, final_k=settings.retrieval_final_k
            )
            retrieved_contexts = [doc.page_content for doc in docs]

        llm_reviewer.enrich_risk(risk, contract_type, clause_text, retrieved_contexts)

        findings.append(AgentFinding(
            clause=risk.clause_no or "",
            risk=risk.severity,
            summary=risk.evidence[:200],
            suggestion=risk.suggestion[:200] if risk.suggestion else None,
        ))

    return AgentOutput(
        agent_id="risk_checker",
        status=AgentStatus.COMPLETED,
        input_summary=f"审查 {len(clauses)} 个条款，发现 {len(findings)} 项风险",
        findings=findings,
        structured_data={
            "risk_findings": [f.model_dump() for f in findings],
        },
        next_agent_hints={
            "has_high_risk": any(f.risk == "high" for f in findings),
            "focus_clauses": [f.clause for f in findings if f.risk == "high"][:3],
        },
        token_used=0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )


def _apply_party_context(risks: list, our_side: str) -> list:
    filtered = []
    for risk in risks:
        if risk.rule_id == "JUR_001" and our_side in risk.evidence:
            continue
        filtered.append(risk)
    return filtered


# ---------------------------------------------------------------------------
# Agent 3: Legal Reference — retrieve relevant laws/regulations
# ---------------------------------------------------------------------------

def legal_ref_agent(ctx: dict[str, Any]) -> AgentOutput:
    findings_data: list[dict] = ctx.get("risk_findings", [])
    contract_type: str = ctx.get("detected_contract_type", settings.default_contract_type)

    if not findings_data:
        return AgentOutput(
            agent_id="legal_ref",
            status=AgentStatus.SKIPPED,
            input_summary="无风险发现，跳过法条引用",
        )

    try:
        vector_store = load_vector_store(settings.knowledge_vector_store_dir)
        retriever = ContractKnowledgeRetriever(vector_store)
    except Exception:
        return AgentOutput(
            agent_id="legal_ref",
            status=AgentStatus.SKIPPED,
            input_summary="知识库不可用，跳过法条引用",
        )

    refs = []
    for fd in findings_data:
        clause = fd.get("clause", "")
        summary = fd.get("summary", "")
        query = f"{contract_type} {summary}"
        docs = retriever.retrieve_documents_with_rerank(
            query=query, fetch_k=settings.retrieval_fetch_k, final_k=2
        )
        for doc in docs:
            refs.append({
                "clause": clause,
                "source": doc.metadata.get("title", "未知"),
                "article": doc.metadata.get("article_label", ""),
                "snippet": doc.page_content[:200],
            })

    return AgentOutput(
        agent_id="legal_ref",
        status=AgentStatus.COMPLETED if refs else AgentStatus.SKIPPED,
        input_summary=f"检索到 {len(refs)} 条法律引用",
        structured_data={"legal_refs": refs},
        token_used=0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Agent 4: Redrafter — generate revision suggestions
# ---------------------------------------------------------------------------

def redrafter_agent(ctx: dict[str, Any]) -> AgentOutput:
    findings_data: list[dict] = ctx.get("risk_findings", [])
    legal_refs: list[dict] = ctx.get("legal_refs", [])

    if not findings_data:
        return AgentOutput(
            agent_id="redrafter",
            status=AgentStatus.SKIPPED,
            input_summary="无风险发现，跳过改写",
        )

    suggestions = []
    for fd in findings_data:
        if not fd.get("suggestion"):
            continue
        suggestions.append({
            "clause": fd.get("clause", ""),
            "original_summary": fd.get("summary", ""),
            "suggestion": fd["suggestion"],
        })

    return AgentOutput(
        agent_id="redrafter",
        status=AgentStatus.COMPLETED,
        input_summary=f"生成 {len(suggestions)} 条改写建议",
        structured_data={"redraft_suggestions": suggestions},
        token_used=0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Agent 5: Summarizer — build final review report
# ---------------------------------------------------------------------------

def summarizer_agent(ctx: dict[str, Any]) -> AgentOutput:
    clauses: list[dict] = ctx.get("parsed_clauses", [])
    findings_data: list[dict] = ctx.get("risk_findings", [])
    legal_refs: list[dict] = ctx.get("legal_refs", [])
    suggestions: list[dict] = ctx.get("redraft_suggestions", [])

    high = sum(1 for f in findings_data if f.get("risk") == "high")
    medium = sum(1 for f in findings_data if f.get("risk") == "medium")
    low = sum(1 for f in findings_data if f.get("risk") == "low")

    if high:
        overall_risk = "high"
    elif medium:
        overall_risk = "medium"
    elif low:
        overall_risk = "low"
    else:
        overall_risk = "info"

    report = {
        "overall_risk": overall_risk,
        "risk_count": len(findings_data),
        "high_count": high,
        "medium_count": medium,
        "low_count": low,
        "clause_count": len(clauses),
        "legal_ref_count": len(legal_refs),
        "suggestion_count": len(suggestions),
        "key_findings": [
            {"clause": f.get("clause", ""), "summary": f.get("summary", ""), "risk": f.get("risk", "info")}
            for f in findings_data[:10]
        ],
    }

    return AgentOutput(
        agent_id="summarizer",
        status=AgentStatus.COMPLETED,
        input_summary=f"生成审核报告：{overall_risk} 风险，共 {len(findings_data)} 项",
        structured_data={"review_report": report},
        token_used=0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
