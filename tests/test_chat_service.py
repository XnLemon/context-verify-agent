import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.react_runtime import ActionReference, ActionResult


class _StubRegistry:
    def __init__(self, action_result: ActionResult) -> None:
        self.action_result = action_result

    def manifest(self):
        return [
            {
                "name": "query_knowledge",
                "description": "stub",
                "input_schema": {"type": "object"},
            }
        ]

    def execute(self, name, context, args):
        return self.action_result


class ChatServiceTests(unittest.TestCase):
    def _payload(self, text: str = "Please provide legal basis for breach liability") -> ChatRequest:
        return ChatRequest(messages=[{"role": "user", "content": text}])

    def test_parse_router_output_uses_json_when_valid(self) -> None:
        service = ChatService.__new__(ChatService)
        payload = self._payload()

        data = service._parse_router_output(
            '{"intent":"search","query":"breach liability legal basis","reason":"user asks for basis"}',
            payload,
        )

        self.assertEqual(data["intent"], "search")
        self.assertEqual(data["query"], "breach liability legal basis")

    def test_parse_router_output_fallback_to_chat(self) -> None:
        service = ChatService.__new__(ChatService)
        payload = self._payload("Hello there")

        data = service._parse_router_output("not-json", payload)

        self.assertEqual(data["intent"], "chat")

    def test_chat_stream_review_keeps_original_logic(self) -> None:
        service = ChatService()
        payload = self._payload("请审查这份合同")
        service._route_intent = Mock(return_value={"intent": "review", "query": "请审查这份合同"})
        service._handle_review = Mock(
            return_value=ChatResponse(
                intent="review",
                tool_used="review",
                answer="review answer",
                generated_at=datetime.now(timezone.utc),
            )
        )
        service._handle_react_stream = Mock()

        events = list(service.chat_stream(payload))

        self.assertEqual(events[0]["event"], "start")
        self.assertEqual(events[-1]["event"], "done")
        service._handle_react_stream.assert_not_called()

    def test_react_stream_query_then_finish_closes_loop(self) -> None:
        service = ChatService()
        payload = self._payload()
        service._route_intent = Mock(return_value={"intent": "chat", "query": "breach liability legal basis"})
        service._require_llm = Mock(return_value=object())
        service._plan_react_step = Mock(
            side_effect=[
                {
                    "thought_summary": "Need evidence first",
                    "action": "query_knowledge",
                    "action_input": {"query": "breach liability legal basis"},
                    "final_answer": "",
                },
                {
                    "thought_summary": "Now enough to answer",
                    "action": "finish",
                    "action_input": {},
                    "final_answer": "Final answer",
                },
            ]
        )
        service._synthesize_react_answer = Mock(return_value="Should not use synthesis")
        service._action_registry = _StubRegistry(
            ActionResult(
                success=True,
                summary="Found one legal snippet.",
                references=[ActionReference(source_title="Civil Code", snippet="Breach liability clause")],
            )
        )

        events = list(service.chat_stream(payload))
        event_names = [item["event"] for item in events]

        self.assertEqual(
            event_names,
            ["start", "reasoning", "action", "observation", "reasoning", "delta", "done"],
        )
        done = events[-1]["data"]
        self.assertEqual(done["tool_used"], "react_query_knowledge")
        self.assertEqual(done["answer"], "Final answer")
        self.assertEqual(len(done["search_results"]), 1)
        self.assertEqual(len(done["trace_summary"]), 2)

    def test_react_stream_action_failure_continues_then_synthesizes(self) -> None:
        service = ChatService()
        payload = self._payload()
        service._route_intent = Mock(return_value={"intent": "advice", "query": "how should I revise clause"})
        service._require_llm = Mock(return_value=object())
        service._plan_react_step = Mock(
            side_effect=[
                {
                    "thought_summary": "Try retrieval first",
                    "action": "query_knowledge",
                    "action_input": {"query": "payment clause risk"},
                    "final_answer": "",
                },
                {
                    "thought_summary": "Failure observed, synthesize anyway",
                    "action": "finish",
                    "action_input": {},
                    "final_answer": "",
                },
            ]
        )
        service._synthesize_react_answer = Mock(return_value="Synthesis answer")
        service._action_registry = _StubRegistry(
            ActionResult(
                success=False,
                summary="Knowledge search failed.",
                error_code="knowledge_search_failed",
                retryable=True,
            )
        )

        events = list(service.chat_stream(payload))
        observations = [item for item in events if item["event"] == "observation"]
        done = events[-1]["data"]

        self.assertEqual(len(observations), 1)
        self.assertFalse(observations[0]["data"]["success"])
        self.assertEqual(done["answer"], "Synthesis answer")
        self.assertEqual(done["trace_summary"][0]["action"], "query_knowledge")

    def test_react_stream_hits_max_steps_and_forces_synthesis(self) -> None:
        service = ChatService()
        payload = self._payload()
        service._route_intent = Mock(return_value={"intent": "search", "query": "dispute resolution clause"})
        service._require_llm = Mock(return_value=object())
        service._plan_react_step = Mock(
            return_value={
                "thought_summary": "Keep querying",
                "action": "query_knowledge",
                "action_input": {"query": "dispute resolution clause"},
                "final_answer": "",
            }
        )
        service._synthesize_react_answer = Mock(return_value="Synthesis after max steps")
        service._action_registry = _StubRegistry(
            ActionResult(
                success=True,
                summary="Found two snippets.",
                references=[ActionReference(source_title="Contract Law", snippet="Dispute resolution guidance")],
            )
        )

        with patch.object(settings, "react_max_steps", 1):
            events = list(service.chat_stream(payload))

        done = events[-1]["data"]
        self.assertEqual(len(done["trace_summary"]), 1)
        self.assertEqual(done["answer"], "Synthesis after max steps")
        service._synthesize_react_answer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
