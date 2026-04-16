from app.data.rules import RULES
from app.schemas.document import ClauseChunk, ParsedDocument
from app.schemas.review import RiskItem


class RuleEngine:
    def check(self, contract_type: str, document: ParsedDocument) -> list[RiskItem]:
        risks: list[RiskItem] = []
        rules = RULES.get("通用合同", []) + RULES.get(contract_type, [])

        for rule in rules:
            if rule.get("check_scope") == "document":
                risk = self._apply_document_rule(rule, document)
                if risk:
                    risks.append(risk)
                continue

            risks.extend(self._apply_clause_rule(rule, document))

        return risks

    def _apply_document_rule(self, rule: dict, document: ParsedDocument) -> RiskItem | None:
        text = document.raw_text
        missing_keywords = rule.get("missing_keywords", [])

        if missing_keywords and not any(keyword in text for keyword in missing_keywords):
            evidence = "合同全文未发现相关关键词。"
            return self._build_risk(rule, evidence)

        return None

    def _apply_clause_rule(self, rule: dict, document: ParsedDocument) -> list[RiskItem]:
        risks: list[RiskItem] = []
        trigger_keywords = rule.get("trigger_keywords", [])
        must_have_any = rule.get("must_have_any", [])
        exclusions = rule.get("exclusions", [])
        requires_cross_clause = rule.get("requires_cross_clause", False)

        for chunk in document.clause_chunks:
            if not trigger_keywords:
                continue
            if not any(keyword in chunk.source_text for keyword in trigger_keywords):
                continue
            if exclusions and any(keyword in chunk.source_text for keyword in exclusions):
                continue
            if must_have_any and any(keyword in chunk.source_text for keyword in must_have_any):
                continue
            if requires_cross_clause and self._has_cross_clause_support(rule, document, chunk):
                continue

            risks.append(self._build_risk(rule, self._find_evidence(chunk, trigger_keywords), chunk))

        return risks

    def _has_cross_clause_support(self, rule: dict, document: ParsedDocument, target_chunk: ClauseChunk) -> bool:
        must_have_any = rule.get("must_have_any", [])
        exclusions = rule.get("exclusions", [])

        for chunk in self._related_chunks(document, target_chunk):
            if chunk.chunk_id == target_chunk.chunk_id:
                continue
            if exclusions and any(keyword in chunk.source_text for keyword in exclusions):
                return True
            if must_have_any and any(keyword in chunk.source_text for keyword in must_have_any):
                return True

        return False

    def _related_chunks(self, document: ParsedDocument, target_chunk: ClauseChunk) -> list[ClauseChunk]:
        related: list[ClauseChunk] = []
        target_root = target_chunk.parent_clause_no or target_chunk.clause_no

        for chunk in document.clause_chunks:
            chunk_root = chunk.parent_clause_no or chunk.clause_no
            if target_root and chunk_root == target_root:
                related.append(chunk)
                continue
            if target_chunk.page_no and chunk.page_no == target_chunk.page_no:
                related.append(chunk)

        return related

    def _find_evidence(self, chunk: ClauseChunk, keywords: list[str]) -> str:
        for line in chunk.source_text.splitlines():
            if any(keyword in line for keyword in keywords):
                return line.strip()
        return chunk.source_text[:120]

    def _build_risk(self, rule: dict, evidence: str, chunk: ClauseChunk | None = None) -> RiskItem:
        return RiskItem(
            rule_id=rule["rule_id"],
            title=rule["title"],
            severity=rule["severity"],
            description=rule["description"],
            evidence=evidence,
            suggestion=rule["suggestion"],
            risk_domain=rule.get("risk_domain"),
            clause_no=chunk.clause_no if chunk else None,
            section_title=chunk.section_title if chunk else None,
            page_no=chunk.page_no if chunk else None,
            start_offset=chunk.start_offset if chunk else None,
            end_offset=chunk.end_offset if chunk else None,
            chunk_level=chunk.chunk_level if chunk else None,
        )
