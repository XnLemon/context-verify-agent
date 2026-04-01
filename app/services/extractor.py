import re

from app.schemas.review import ExtractedFields


class ContractExtractor:
    def extract(self, text: str) -> ExtractedFields:
        return ExtractedFields(
            contract_name=self._extract_contract_name(text),
            party_a=self._extract_party(text, "甲方"),
            party_b=self._extract_party(text, "乙方"),
            amount=self._extract_amount(text),
            dispute_clause=self._extract_dispute_clause(text),
        )

    def _extract_contract_name(self, text: str) -> str | None:
        first_line = text.strip().splitlines()[0] if text.strip() else ""
        return first_line[:100] or None

    def _extract_party(self, text: str, role: str) -> str | None:
        match = re.search(rf"{role}\s*[:：]\s*([^\n]+)", text)
        return match.group(1).strip() if match else None

    def _extract_amount(self, text: str) -> str | None:
        patterns = [
            r"(?:合同总价|合同金额|价税合计|总金额)\s*[:：]?\s*(人民币)?\s*([0-9]+(?:\.[0-9]+)?)\s*元",
            r"(人民币\s*[0-9]+(?:\.[0-9]+)?\s*元)",
            r"([0-9]+(?:\.[0-9]+)?\s*元)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            groups = [group for group in match.groups() if group]
            return "".join(groups).replace(" ", "") if groups else match.group(0).replace(" ", "")
        return None

    def _extract_dispute_clause(self, text: str) -> str | None:
        for line in text.splitlines():
            stripped = line.strip()
            if "争议" in stripped or "管辖" in stripped or "仲裁" in stripped:
                return stripped
        return None
