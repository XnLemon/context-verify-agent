from app.schemas.review import RiskItem

from app.llm.client import get_chat_model
from app.llm.prompts import risk_explain_prompt


class LLMReviewer:
    def __init__(self) -> None:
        self.llm = get_chat_model()

    def enrich_risk(
        self,
        risk: RiskItem,
        contract_type: str,
        clause_text: str,
        retrieved_contexts: list[str],
    ) -> RiskItem:
        context_text = "\n\n".join(retrieved_contexts) if retrieved_contexts else "无额外检索上下文"
        chain = risk_explain_prompt | self.llm
        result = chain.invoke(
            {
                "contract_type": contract_type,
                "title": risk.title,
                "risk_domain": risk.risk_domain or "未分类",
                "description": risk.description,
                "evidence": risk.evidence,
                "clause_text": clause_text,
                "retrieved_context": context_text,
            }
        )
        risk.ai_explanation = result.content
        risk.retrieved_contexts = retrieved_contexts
        return risk
