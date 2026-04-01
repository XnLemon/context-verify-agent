import unittest

from langchain_core.documents import Document

from app.schemas.review import ReviewRequest
from app.services.parser import ContractParser
from app.services.review_service import ReviewService


SAMPLE_TEXT = """采购合同
甲方：甲公司
乙方：乙公司
第一条 标的
乙方应交付服务器设备。
第二条 付款方式
甲方应于合同签订后5日内支付100%合同价款。
2.1 首付款
甲方在合同生效后支付30%。
2.2 尾款
验收合格后支付70%。
第三条 争议解决
争议由乙方所在地人民法院管辖。"""


class FakeRetriever:
    def retrieve_documents(self, query: str, k: int = 3):
        return [
            Document(
                page_content="第一百零九条 当事人应当按照约定全面履行自己的义务。",
                metadata={"title": "民法典合同编", "article_label": "第一百零九条", "source_path": "knowledge/laws/民法典.txt"},
            )
        ]


class FakeLLMReviewer:
    def enrich_risk(self, risk, contract_type: str, clause_text: str, retrieved_contexts: list[str]):
        risk.ai_explanation = f"{contract_type}:{risk.title}"
        return risk


class ChunkerTests(unittest.TestCase):
    def test_parse_text_splits_expected_chunks(self) -> None:
        document = ContractParser().parse_text(SAMPLE_TEXT)

        self.assertEqual(document.metadata.title, "采购合同")
        self.assertEqual(len(document.clause_chunks), 6)

        levels = [chunk.chunk_level for chunk in document.clause_chunks]
        self.assertEqual(levels, ["preface", "clause", "clause", "sub_clause", "sub_clause", "clause"])

        payment_sub_clause = document.clause_chunks[3]
        self.assertEqual(payment_sub_clause.clause_no, "2.1")
        self.assertEqual(payment_sub_clause.parent_clause_no, "第二条")
        self.assertEqual(payment_sub_clause.section_title, "首付款")

    def test_cross_clause_rule_uses_acceptance_context(self) -> None:
        review_service = ReviewService()
        review_service._require_llm_reviewer = lambda: FakeLLMReviewer()
        review_service._require_knowledge_retriever = lambda: FakeRetriever()
        result = review_service.review(ReviewRequest(contract_text=SAMPLE_TEXT, contract_type="采购合同"))

        risk_ids = {risk.rule_id for risk in result.risks}
        self.assertIn("JUR_001", risk_ids)
        self.assertNotIn("PAY_001", risk_ids)


if __name__ == "__main__":
    unittest.main()
