import unittest

from langchain_core.documents import Document

from app.core.config import settings
from app.schemas.review import ReviewRequest
from app.services.review_service import ReviewService


SAMPLE_TEXT = """采购合同
甲方：甲公司
乙方：乙公司
第一条 标的
乙方应交付服务器设备。
第二条 付款方式
甲方应于合同签订后5日内支付100%合同价款。
第三条 争议解决
争议由乙方所在地人民法院管辖。"""


class FakeRetriever:
    def retrieve_documents(self, query: str, k: int = 3):
        return [
            Document(
                page_content="第一百零九条 当事人应当按照约定全面履行自己的义务。",
                metadata={
                    "title": "民法典合同编",
                    "article_label": "第一百零九条",
                    "source_path": "knowledge/laws/民法典.txt",
                },
            )
        ]


class FakeLLMReviewer:
    def enrich_risk(self, risk, contract_type: str, clause_text: str, retrieved_contexts: list[str]):
        risk.ai_explanation = f"{contract_type}存在风险：{risk.title}"
        return risk


class ReviewServiceTests(unittest.TestCase):
    def test_review_builds_report_and_basis_sources(self) -> None:
        service = ReviewService()
        service._require_llm_reviewer = lambda: FakeLLMReviewer()
        service._require_knowledge_retriever = lambda: FakeRetriever()

        response = service.review(ReviewRequest(contract_text=SAMPLE_TEXT, contract_type="采购合同"))

        self.assertGreaterEqual(response.summary.risk_count, 1)
        self.assertTrue(response.report.overview)
        self.assertTrue(response.report.generated_at)
        self.assertTrue(response.risks[0].basis_sources)
        self.assertIn("民法典合同编", response.risks[0].basis_sources[0].source_title)
        self.assertTrue(response.risks[0].ai_explanation)

    def test_missing_llm_config_raises_runtime_error(self) -> None:
        service = ReviewService()
        original = settings.qwen_api_key
        settings.qwen_api_key = None
        try:
            with self.assertRaises(RuntimeError):
                service._require_llm_reviewer()
        finally:
            settings.qwen_api_key = original

    def test_vector_store_failure_is_wrapped(self) -> None:
        service = ReviewService()
        original_dir = settings.knowledge_vector_store_dir
        settings.knowledge_vector_store_dir = "."
        try:
            with unittest.mock.patch("app.services.review_service.load_vector_store", side_effect=ValueError("broken index")):
                with self.assertRaises(RuntimeError) as ctx:
                    service._require_knowledge_retriever()
            self.assertIn("法律知识库加载失败", str(ctx.exception))
        finally:
            settings.knowledge_vector_store_dir = original_dir


if __name__ == "__main__":
    unittest.main()
