from __future__ import annotations

import pytest
from app.multi_agent.gateway import GatewayRouter
from app.multi_agent.protocol import AgentMode


class TestGatewayRouter:
    def setup_method(self):
        self.router = GatewayRouter()

    def test_routes_review_keyword_to_review_team(self):
        resp = self.router.route("帮我审查这个合同")
        assert resp.team == "review"

    def test_routes_generic_question_to_dialogue(self):
        resp = self.router.route("第8条是什么意思")
        assert resp.team == "dialogue"

    def test_simple_keyword_selects_single_mode(self):
        resp = self.router.route("简单看一下这个合同")
        assert resp.mode == AgentMode.SINGLE

    def test_deep_keyword_selects_multi_manual(self):
        resp = self.router.route("深度审查这份合同")
        assert resp.mode == AgentMode.MULTI_MANUAL

    def test_large_contract_triggers_multi_manual(self):
        resp = self.router.route("帮我审查合同", contract_clause_count=60)
        assert resp.mode == AgentMode.MULTI_MANUAL

    def test_explicit_mode_overrides_detection(self):
        resp = self.router.route("帮我审查合同", explicit_mode=AgentMode.SINGLE)
        assert resp.mode == AgentMode.SINGLE
        assert resp.team == "review"
