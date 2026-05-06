from __future__ import annotations

import unittest

from app.multi_agent.agents import parser_agent, summarizer_agent


class ParserAgentTests(unittest.TestCase):
    def test_parser_agent_returns_clauses(self):
        result = parser_agent({
            "contract_text": "第一条 定义\n1.1 甲方：张三\n第二条 付款\n2.1 付款方式：月付",
        })
        self.assertEqual(result.agent_id, "parser")
        self.assertEqual(result.status.value, "completed")
        clauses = result.structured_data.get("parsed_clauses", [])
        self.assertGreater(len(clauses), 0)
        self.assertTrue(any("第一条" in c.get("text", "") for c in clauses))


class SummarizerAgentTests(unittest.TestCase):
    def test_summarizer_with_empty_findings(self):
        result = summarizer_agent({
            "parsed_clauses": [{"clause_no": "1", "text": "test"}],
            "risk_findings": [],
            "legal_refs": [],
            "redraft_suggestions": [],
        })
        self.assertEqual(result.agent_id, "summarizer")
        report = result.structured_data.get("review_report", {})
        self.assertEqual(report.get("overall_risk"), "info")
        self.assertEqual(report.get("risk_count"), 0)

    def test_summarizer_with_findings(self):
        result = summarizer_agent({
            "parsed_clauses": [{"clause_no": "1", "text": "test"}],
            "risk_findings": [
                {"clause": "1", "risk": "high", "summary": "高风险条款"},
                {"clause": "2", "risk": "low", "summary": "低风险条款"},
            ],
            "legal_refs": [{"clause": "1", "source": "民法典"}],
            "redraft_suggestions": [{"clause": "1", "suggestion": "修改为..."}],
        })
        report = result.structured_data.get("review_report", {})
        self.assertEqual(report.get("overall_risk"), "high")
        self.assertEqual(report.get("risk_count"), 2)
        self.assertEqual(report.get("high_count"), 1)
        self.assertEqual(report.get("low_count"), 1)
        self.assertEqual(report.get("legal_ref_count"), 1)
        self.assertEqual(report.get("suggestion_count"), 1)
