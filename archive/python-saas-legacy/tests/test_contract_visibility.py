import tempfile
import unittest
from datetime import datetime, timezone

from app.schemas.auth import MemberPublic
from app.services.workbench_repository import WorkbenchRepository
from app.services.workbench_service import WorkbenchService


class ContractVisibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repository = WorkbenchRepository(base_dir=self.tempdir.name)
        self.service = WorkbenchService(repository=self.repository)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _member(self, username: str, member_type: str = "business") -> MemberPublic:
        return MemberPublic(
            id=1,
            username=username,
            display_name=username,
            role="employee",
            member_type=member_type,
            is_active=True,
            last_login_at=None,
            created_at=datetime.now(timezone.utc),
        )

    def test_employee_can_only_list_owned_contracts(self) -> None:
        owner = self._member("u1")

        response = self.service.list_contracts(current_member=owner)

        self.assertEqual(response.total, 1)
        self.assertEqual(response.items[0].id, "contract-001")

    def test_employee_cannot_access_other_contract_detail(self) -> None:
        owner = self._member("u1")

        with self.assertRaises(KeyError):
            self.service.get_contract_detail("contract-002", current_member=owner)

    def test_legal_member_can_access_all_contracts(self) -> None:
        legal_member = self._member("legal-1", member_type="legal")

        response = self.service.list_contracts(current_member=legal_member)

        self.assertEqual(response.total, 4)


if __name__ == "__main__":
    unittest.main()
