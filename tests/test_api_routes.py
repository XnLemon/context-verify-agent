import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.review import ExtractedFields, ReviewReport, ReviewResponse, ReviewSummary


class ApiRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_demo_page_returns_html(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("合同校审演示台", response.text)

    def test_health_returns_runtime_flags(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("llm_configured", payload)
        self.assertIn("knowledge_base_ready", payload)

    def test_review_runtime_error_returns_503(self) -> None:
        with patch("app.api.routes.review_service.review", side_effect=RuntimeError("QWEN_API_KEY 未配置")):
            response = self.client.post(
                "/review",
                json={"contract_text": "采购合同\n甲方：甲公司\n乙方：乙公司"},
            )

        self.assertEqual(response.status_code, 503)

    def test_parse_requires_upload_not_file_path(self) -> None:
        response = self.client.post("/parse", json={"file_path": "C:/secret.txt"})
        self.assertEqual(response.status_code, 422)

    def test_parse_accepts_upload(self) -> None:
        with patch("app.api.routes.review_service.parse_file") as parse_file:
            parse_file.return_value = {
                "metadata": {"doc_id": "doc_1", "file_name": "contract.txt", "file_type": "txt", "source_path": "contract.txt", "page_count": 1},
                "raw_text": "采购合同",
                "spans": [],
                "clause_chunks": [],
            }
            response = self.client.post(
                "/parse",
                files={"file": ("contract.txt", "采购合同".encode("utf-8"), "text/plain")},
            )

        self.assertEqual(response.status_code, 200)

    def test_review_file_rejects_unsupported_suffix(self) -> None:
        response = self.client.post(
            "/review/file",
            files={"file": ("contract.exe", b"demo", "application/octet-stream")},
            data={"our_side": "甲方"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file type", response.json()["detail"])

    def test_review_file_accepts_upload(self) -> None:
        fake_response = ReviewResponse(
            summary=ReviewSummary(contract_type="采购合同", overall_risk="medium", risk_count=1),
            extracted_fields=ExtractedFields(contract_name="采购合同"),
            risks=[],
            report=ReviewReport(
                generated_at="2026-04-01T00:00:00Z",
                overview="ok",
                key_findings=["test"],
                next_actions=["fix"],
            ),
        )
        with patch("app.api.routes.review_service.review_file", return_value=fake_response):
            response = self.client.post(
                "/review/file",
                files={"file": ("contract.txt", "采购合同\n甲方：甲公司\n乙方：乙公司".encode("utf-8"), "text/plain")},
                data={"our_side": "甲方"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summary"]["contract_type"], "采购合同")


if __name__ == "__main__":
    unittest.main()
