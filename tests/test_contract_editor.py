import unittest

from app.llm.editor import ContractEditor


class ContractEditorSegmentationTests(unittest.TestCase):
    def setUp(self) -> None:
        # Skip __init__ to avoid real model initialization in unit tests.
        self.editor = ContractEditor.__new__(ContractEditor)

    def test_build_segments_splits_long_contract(self) -> None:
        text = "\n".join(
            [
                "采购合同",
                "第一条 标的",
                "甲方采购服务器。",
                "第二条 付款方式",
                "甲方分阶段支付。",
                "第三条 违约责任",
                "违约方承担责任。",
            ]
        )
        segments = self.editor._build_segments(text, max_chunk_chars=20)
        self.assertGreaterEqual(len(segments), 2)
        self.assertTrue(all(len(item) <= 20 for item in segments))

    def test_select_relevant_issues_matches_location(self) -> None:
        segment = "第二条 付款方式\n甲方分阶段支付。"
        issues = [
            {"message": "付款比例过高", "suggestion": "改为分阶段付款", "location": "第二条"},
            {"message": "争议解决条款", "suggestion": "修改管辖", "location": "第三条"},
        ]
        related = self.editor._select_relevant_issues(segment, issues)
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]["location"], "第二条")


if __name__ == "__main__":
    unittest.main()
