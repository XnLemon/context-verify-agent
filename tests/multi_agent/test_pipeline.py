from __future__ import annotations

import unittest

from app.multi_agent.gateway import GatewayRouter
from app.multi_agent.pipeline import PipelineOrchestrator
from app.multi_agent.protocol import PipelineStatus
from app.multi_agent.agents import parser_agent, summarizer_agent


class PipelineIntegrationTests(unittest.TestCase):
    def test_review_pipeline_parser_to_summarizer(self):
        """Minimal pipeline test: parser -> summarizer (skipping middle agents)."""
        orchestrator = PipelineOrchestrator()
        orchestrator.register_agent("parser", parser_agent)
        orchestrator.register_agent("summarizer", summarizer_agent)
        orchestrator.register_route("parser", "success", "summarizer")

        gateway = GatewayRouter()
        resp = gateway.route("审查合同")
        state = gateway.create_pipeline_state(resp, contract_id="test-1")

        result = orchestrator.run(state, {"contract_text": "第一条 付款\n1.1 甲方应在30日内付款"})
        self.assertEqual(result.status, PipelineStatus.COMPLETED)
        self.assertIn("parser", result.agent_outputs)
        self.assertIn("summarizer", result.agent_outputs)

    def test_pipeline_cancellation(self):
        orchestrator = PipelineOrchestrator()
        orchestrator.register_agent("parser", parser_agent)

        gateway = GatewayRouter()
        resp = gateway.route("审查合同")
        state = gateway.create_pipeline_state(resp, contract_id="test-2")

        orchestrator.cancel(state)
        result = orchestrator.run(state, {"contract_text": "test"})
        self.assertEqual(result.status, PipelineStatus.CANCELLED)
