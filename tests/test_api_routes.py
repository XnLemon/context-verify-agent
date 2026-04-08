import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.auth import MemberPublic
from app.schemas.chat import ChatResponse
from app.schemas.review import ExtractedFields, ReviewReport, ReviewResponse, ReviewSummary
from app.schemas.workbench import (
    WorkbenchChatMessage,
    WorkbenchChatResponse,
    WorkbenchContractDetailResponse,
    WorkbenchContractListItem,
    WorkbenchContractListResponse,
    WorkbenchContractUpdateResponse,
    WorkbenchHistoryItem,
    WorkbenchImportResponse,
    WorkbenchIssue,
    WorkbenchRedraftResponse,
    WorkbenchReviewResult,
    WorkbenchScanResponse,
    WorkbenchSummaryResponse,
)


class ApiRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_demo_page_returns_html(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="root"', response.text)

    def test_health_returns_runtime_flags(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("llm_configured", payload)
        self.assertIn("knowledge_base_ready", payload)

    def test_workbench_summary_returns_cards(self) -> None:
        fake_response = WorkbenchSummaryResponse(
            pendingCount=3,
            complianceRate=94.2,
            highRiskCount=2,
            averageReviewDurationHours=1.5,
            totalContracts=4,
        )
        with patch("app.api.routes.workbench_service.get_summary", return_value=fake_response):
            response = self.client.get("/api/workbench/summary")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pendingCount"], 3)

    def test_workbench_contracts_returns_list(self) -> None:
        fake_response = WorkbenchContractListResponse(
            items=[
                WorkbenchContractListItem(
                    id="contract-001",
                    title="采购合同",
                    type="采购合同",
                    status="reviewing",
                    updatedAt="2026-04-07 10:00",
                    author="李明",
                    content="合同正文",
                )
            ],
            total=1,
        )
        with patch("app.api.routes.workbench_service.list_contracts", return_value=fake_response):
            response = self.client.get("/api/workbench/contracts", params={"status": "reviewing"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["id"], "contract-001")

    def test_workbench_detail_returns_404_for_unknown_contract(self) -> None:
        with patch("app.api.routes.workbench_service.get_contract_detail", side_effect=KeyError("missing")):
            response = self.client.get("/api/workbench/contracts/missing")

        self.assertEqual(response.status_code, 404)

    def test_workbench_scan_returns_review_payload(self) -> None:
        review = WorkbenchReviewResult(
            summary=ReviewSummary(contract_type="采购合同", overall_risk="medium", risk_count=1),
            reportOverview="已完成扫描",
            keyFindings=["付款条款可能早于验收"],
            nextActions=["补充验收条款"],
            issues=[
                WorkbenchIssue(
                    id="PAY_001-1-1",
                    type="risk",
                    severity="high",
                    message="付款条款可能早于验收",
                    suggestion="补充验收条款",
                    location="第二条 | 付款方式",
                )
            ],
            generatedAt=datetime.now(timezone.utc),
        )
        fake_response = WorkbenchScanResponse(
            contract=WorkbenchContractListItem(
                id="contract-001",
                title="采购合同",
                type="采购合同",
                status="reviewing",
                updatedAt="2026-04-07 10:00",
                author="李明",
                content="合同正文",
            ),
            latestReview=review,
            historyCount=2,
        )
        with patch("app.api.routes.workbench_service.scan_contract", return_value=fake_response):
            response = self.client.post("/api/workbench/contracts/contract-001/scan", data={"our_side": "甲方"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["latestReview"]["summary"]["risk_count"], 1)

    def test_workbench_chat_returns_thread_payload(self) -> None:
        assistant_message = WorkbenchChatMessage(
            id="msg-1",
            role="assistant",
            content="这是 AI 回复",
            timestamp="10:00",
            created_at=datetime.now(timezone.utc),
        )
        fake_response = WorkbenchChatResponse(
            intent="chat",
            toolUsed="chat",
            assistantMessage=assistant_message,
            messages=[assistant_message],
            latestReview=None,
        )
        with patch("app.api.routes.workbench_service.chat_contract", return_value=fake_response):
            response = self.client.post(
                "/api/workbench/contracts/contract-001/chat",
                json={"message": "帮我解释争议条款"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["assistantMessage"]["content"], "这是 AI 回复")

    def test_workbench_history_returns_items(self) -> None:
        fake_history = [
            WorkbenchHistoryItem(
                id="history-1",
                type="scan",
                title="完成合同扫描",
                description="识别到 1 项风险。",
                createdAt=datetime.now(timezone.utc),
                metadata={},
            )
        ]
        with patch("app.api.routes.workbench_service.get_history", return_value=fake_history):
            response = self.client.get("/api/workbench/contracts/contract-001/history")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["type"], "scan")

    def test_workbench_update_contract_returns_payload(self) -> None:
        fake_response = WorkbenchContractUpdateResponse(
            contract=WorkbenchContractListItem(
                id="contract-001",
                title="采购合同",
                type="采购合同",
                status="pending",
                updatedAt="2026-04-07 10:00",
                author="李明",
                content="更新后的正文",
            )
        )
        with patch("app.api.routes.workbench_service.update_contract_content", return_value=fake_response):
            response = self.client.patch(
                "/api/workbench/contracts/contract-001",
                json={"content": "更新后的正文"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["contract"]["content"], "更新后的正文")
    def test_workbench_import_accepts_upload(self) -> None:
        fake_response = WorkbenchImportResponse(
            contract=WorkbenchContractListItem(
                id="contract-new",
                title="新合同",
                type="采购合同",
                status="pending",
                updatedAt="2026-04-07 10:00",
                author="系统导入",
                content="合同正文",
            )
        )
        with patch("app.api.routes.workbench_service.import_contract", return_value=fake_response):
            response = self.client.post(
                "/api/workbench/contracts/import",
                files={"file": ("contract.txt", b"contract", "text/plain")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["contract"]["id"], "contract-new")

    def test_review_runtime_error_returns_503(self) -> None:
        with patch("app.api.routes.review_service.review", side_effect=RuntimeError("QWEN_API_KEY missing")):
            response = self.client.post(
                "/review",
                json={"contract_text": "contract text"},
            )

        self.assertEqual(response.status_code, 503)

    def test_parse_requires_upload_not_file_path(self) -> None:
        response = self.client.post("/parse", json={"file_path": "C:/secret.txt"})
        self.assertEqual(response.status_code, 422)

    def test_parse_accepts_upload(self) -> None:
        with patch("app.api.routes.review_service.parse_file") as parse_file:
            parse_file.return_value = {
                "metadata": {"doc_id": "doc_1", "file_name": "contract.txt", "file_type": "txt", "source_path": "contract.txt", "page_count": 1},
                "raw_text": "contract",
                "spans": [],
                "clause_chunks": [],
            }
            response = self.client.post(
                "/parse",
                files={"file": ("contract.txt", b"contract", "text/plain")},
            )

        self.assertEqual(response.status_code, 200)

    def test_review_file_rejects_unsupported_suffix(self) -> None:
        response = self.client.post(
            "/review/file",
            files={"file": ("contract.exe", b"demo", "application/octet-stream")},
            data={"our_side": "A"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file type", response.json()["detail"])

    def test_review_file_accepts_upload(self) -> None:
        fake_response = ReviewResponse(
            summary=ReviewSummary(contract_type="procurement", overall_risk="medium", risk_count=1),
            extracted_fields=ExtractedFields(contract_name="contract"),
            risks=[],
            report=ReviewReport(
                generated_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                overview="ok",
                key_findings=["test"],
                next_actions=["fix"],
            ),
        )
        with patch("app.api.routes.review_service.review_file", return_value=fake_response):
            response = self.client.post(
                "/review/file",
                files={"file": ("contract.txt", b"contract", "text/plain")},
                data={"our_side": "A"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summary"]["contract_type"], "procurement")

    def test_chat_returns_routed_response(self) -> None:
        fake_response = ChatResponse(
            intent="search",
            tool_used="knowledge_search",
            answer="search summary",
            generated_at=datetime.now(timezone.utc),
            search_results=[],
            review_result=None,
        )
        with patch("app.api.routes.chat_service.chat", return_value=fake_response):
            response = self.client.post(
                "/chat",
                json={"messages": [{"role": "user", "content": "find dispute clause law"}]},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tool_used"], "knowledge_search")

    def test_chat_runtime_error_returns_503(self) -> None:
        with patch("app.api.routes.chat_service.chat", side_effect=RuntimeError("knowledge base load failed")):
            response = self.client.post(
                "/chat",
                json={"messages": [{"role": "user", "content": "find dispute clause law"}]},
            )

        self.assertEqual(response.status_code, 503)


    def test_workbench_redraft_returns_contract_payload(self) -> None:
        review = WorkbenchReviewResult(
            summary=ReviewSummary(contract_type="????", overall_risk="medium", risk_count=1),
            reportOverview="?????",
            keyFindings=["??????????"],
            nextActions=["??????"],
            issues=[
                WorkbenchIssue(
                    id="PAY_001-1-1",
                    type="risk",
                    severity="high",
                    message="??????????",
                    suggestion="??????",
                    location="??? | ????",
                    status="accepted",
                )
            ],
            generatedAt=datetime.now(timezone.utc),
        )
        fake_response = WorkbenchRedraftResponse(
            contract=WorkbenchContractListItem(
                id="contract-001",
                title="????",
                type="????",
                status="reviewing",
                updatedAt="2026-04-07 10:00",
                author="??",
                content="????????",
            ),
            latestReview=review,
            acceptedIssueCount=1,
        )
        with patch("app.api.routes.workbench_service.redraft_contract", return_value=fake_response):
            response = self.client.post(
                "/api/workbench/contracts/contract-001/redraft",
                json={"our_side": "??"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["acceptedIssueCount"], 1)
        self.assertEqual(response.json()["contract"]["content"], "????????")



    def test_auth_login_challenge_returns_nonce_and_salt(self) -> None:
        fake_challenge = {
            "challenge_token": "challenge-1",
            "nonce": "nonce-1",
            "salt": "salt-1",
            "expires_at": "2026-04-08T10:00:00Z",
        }
        with patch("app.api.routes.auth_service.issue_login_challenge", return_value=fake_challenge):
            response = self.client.post("/api/auth/login/challenge", json={"username": "admin"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["challenge_token"], "challenge-1")
    def test_auth_login_returns_member_and_token(self) -> None:
        fake_response = {
            "token": "token-1",
            "expires_at": "2026-04-08T10:00:00Z",
            "member": {
                "id": 1,
                "username": "admin",
                "display_name": "系统管理员",
                "role": "admin",
                "member_type": "admin",
                "is_active": True,
                "last_login_at": None,
                "created_at": "2026-04-07T10:00:00Z",
            },
        }
        with patch("app.api.routes.auth_service.login_with_proof", return_value=fake_response):
            response = self.client.post("/api/auth/login", json={"username": "admin", "challenge_token": "token-123", "password_proof": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["member"]["role"], "admin")

    def test_auth_me_returns_401_without_token(self) -> None:
        with patch("app.api.routes.auth_service.authenticate_bearer", side_effect=PermissionError("缺少登录凭证")):
            response = self.client.get("/api/auth/me")

        self.assertEqual(response.status_code, 401)

    def test_admin_create_employee_forbidden_for_non_admin(self) -> None:
        employee_member = MemberPublic(
            id=2,
            username="u1",
            display_name="员工1",
            role="employee",
            member_type="legal",
            is_active=True,
            last_login_at=None,
            created_at=datetime.now(timezone.utc),
        )
        with patch("app.api.routes.auth_service.authenticate_bearer", return_value=employee_member):
            response = self.client.post(
                "/api/admin/employees",
                headers={"Authorization": "Bearer mock-token"},
                json={"username": "new1", "password": "123456", "display_name": "新员工", "member_type": "legal"},
            )

        self.assertEqual(response.status_code, 403)
if __name__ == "__main__":
    unittest.main()







