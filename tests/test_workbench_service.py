import tempfile
import unittest
from datetime import datetime, timezone

from app.schemas.chat import ChatResponse
from app.schemas.document import DocumentMetadata, ParsedDocument
from app.schemas.review import ExtractedFields, ReviewReport, ReviewResponse, ReviewSummary, RiskItem
from app.schemas.workbench import WorkbenchChatRequest, WorkbenchIssueDecisionRequest
from app.services.workbench_repository import WorkbenchRepository
from app.services.workbench_service import WorkbenchService


class FakeReviewService:
    def review(self, payload):
        return ReviewResponse(
            summary=ReviewSummary(contract_type=payload.contract_type or "�ɹ���ͬ", overall_risk="medium", risk_count=1),
            extracted_fields=ExtractedFields(contract_name="���Ժ�ͬ"),
            risks=[
                RiskItem(
                    rule_id="PAY_001",
                    title="�������������������",
                    severity="high",
                    description="desc",
                    evidence="�׷�Ӧ�ں�ͬǩ����5����֧��100%��ͬ�ۿ",
                    suggestion="�����Ϊ�ֽ׶θ��",
                    risk_domain="����",
                    clause_no="�ڶ���",
                    section_title="���ʽ",
                    start_offset=12,
                    end_offset=32,
                )
            ],
            report=ReviewReport(
                generated_at=datetime(2026, 4, 7, tzinfo=timezone.utc),
                overview="�����У��",
                key_findings=["�������������������"],
                next_actions=["�����Ϊ�ֽ׶θ��"],
            ),
        )

    def parse_file(self, file_name, content):
        return ParsedDocument(
            metadata=DocumentMetadata(
                doc_id="doc-1",
                file_name=file_name,
                file_type="txt",
                source_path=file_name,
                title="�����ͬ",
                contract_type_hint="�ɹ���ͬ",
                page_count=1,
            ),
            raw_text=content.decode("utf-8"),
            spans=[],
            clause_chunks=[],
        )




class FakeContractEditor:
    def redraft_contract(self, *, contract_text: str, contract_type: str, our_side: str, accepted_issues: list[dict[str, str]]) -> str:
        return contract_text + "\n\n?AI????????????????"


class FakeChatService:
    def __init__(self):
        self.return_review = False

    def chat(self, payload):
        review_result = FakeReviewService().review(type("Payload", (), {"contract_type": payload.contract_type})) if self.return_review else None
        return ChatResponse(
            intent="review" if self.return_review else "chat",
            tool_used="review" if self.return_review else "chat",
            answer="���ǻ��ں�ͬ�Ļظ���",
            generated_at=datetime.now(timezone.utc),
            search_results=[],
            review_result=review_result,
        )


class WorkbenchServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repository = WorkbenchRepository(base_dir=self.tempdir.name)
        self.chat_service = FakeChatService()
        self.service = WorkbenchService(
            repository=self.repository,
            review_service=FakeReviewService(),
            chat_service=self.chat_service,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_list_contracts_returns_seed_data(self) -> None:
        response = self.service.list_contracts()

        self.assertEqual(response.total, 4)
        self.assertTrue(any(item.id == "contract-001" for item in response.items))

    def test_get_contract_detail_returns_content_and_status(self) -> None:
        response = self.service.get_contract_detail("contract-001")

        self.assertEqual(response.contract.id, "contract-001")
        self.assertEqual(response.contract.status, "reviewing")
        self.assertIn("第一条", response.contract.content)

    def test_scan_contract_persists_latest_review(self) -> None:
        response = self.service.scan_contract("contract-001")
        detail = self.service.get_contract_detail("contract-001")

        self.assertEqual(response.latestReview.summary.risk_count, 1)
        self.assertEqual(detail.latestReview.issues[0].id, "PAY_001-12-1")
        self.assertEqual(detail.contract.status, "reviewing")

    def test_issue_decision_is_persisted(self) -> None:
        self.service.scan_contract("contract-001")

        review = self.service.decide_issue(
            "contract-001",
            "PAY_001-12-1",
            WorkbenchIssueDecisionRequest(status="accepted"),
        )
        detail = self.service.get_contract_detail("contract-001")

        self.assertEqual(review.issues[0].status, "accepted")
        self.assertEqual(detail.latestReview.issues[0].status, "accepted")
        self.assertEqual(detail.contract.status, "approved")

    def test_chat_contract_persists_messages_and_history(self) -> None:
        response = self.service.chat_contract("contract-001", payload=WorkbenchChatRequest(message="�������������"))
        detail = self.service.get_contract_detail("contract-001")
        history = self.service.get_history("contract-001")

        self.assertEqual(response.assistantMessage.role, "assistant")
        self.assertEqual(len(detail.chatMessages), 2)
        self.assertEqual(history[0].type, "chat")

    def test_chat_contract_can_persist_review_result(self) -> None:
        self.chat_service.return_review = True

        response = self.service.chat_contract("contract-001", payload=WorkbenchChatRequest(message="���������"))
        detail = self.service.get_contract_detail("contract-001")

        self.assertEqual(response.intent, "review")
        self.assertIsNotNone(response.latestReview)
        self.assertIsNotNone(detail.latestReview)

    def test_import_contract_creates_new_record(self) -> None:
        response = self.service.import_contract(file_name="new.txt", content="����ĺ�ͬ����".encode("utf-8"))
        detail = self.service.get_contract_detail(response.contract.id)

        self.assertEqual(response.contract.title, "�����ͬ")
        self.assertEqual(detail.contract.author, "系统导入")
        self.assertEqual(self.service.list_contracts().total, 5)

    def test_update_contract_content_persists_and_sets_pending(self) -> None:
        response = self.service.update_contract_content("contract-001", "手动修改后的合同正文")
        detail = self.service.get_contract_detail("contract-001")
        history = self.service.get_history("contract-001")

        self.assertEqual(response.contract.content, "手动修改后的合同正文")
        self.assertEqual(detail.contract.content, "手动修改后的合同正文")
        self.assertEqual(detail.contract.status, "pending")
        self.assertEqual(history[0].type, "manual_edit")
    def test_missing_contract_raises_key_error(self) -> None:
        with self.assertRaises(KeyError):
            self.service.get_contract_detail("missing")


    def test_redraft_contract_updates_content(self) -> None:
        self.service.scan_contract("contract-001")
        self.service._contract_editor = FakeContractEditor()
        self.service.decide_issue(
            "contract-001",
            "PAY_001-12-1",
            WorkbenchIssueDecisionRequest(status="accepted", auto_redraft=False),
        )

        response = self.service.redraft_contract("contract-001", our_side="??")
        detail = self.service.get_contract_detail("contract-001")

        self.assertEqual(response.acceptedIssueCount, 1)
        self.assertIn("AI???", response.contract.content)
        self.assertIn("AI???", detail.contract.content)

    def test_decide_issue_can_auto_redraft(self) -> None:
        self.service.scan_contract("contract-001")
        self.service._contract_editor = FakeContractEditor()

        self.service.decide_issue(
            "contract-001",
            "PAY_001-12-1",
            WorkbenchIssueDecisionRequest(status="accepted", auto_redraft=True),
        )
        detail = self.service.get_contract_detail("contract-001")

        self.assertIn("AI???", detail.contract.content)


    def test_rescan_resets_issue_status_to_pending(self) -> None:
        self.service.scan_contract("contract-001")
        self.service.decide_issue(
            "contract-001",
            "PAY_001-12-1",
            WorkbenchIssueDecisionRequest(status="accepted", auto_redraft=False),
        )

        before_rescan = self.service.get_contract_detail("contract-001")
        self.assertEqual(before_rescan.contract.status, "approved")
        self.assertEqual(before_rescan.latestReview.issues[0].status, "accepted")

        self.service.scan_contract("contract-001")
        after_rescan = self.service.get_contract_detail("contract-001")

        self.assertEqual(after_rescan.contract.status, "reviewing")
        self.assertEqual(after_rescan.latestReview.issues[0].status, "pending")

if __name__ == "__main__":
    unittest.main()



