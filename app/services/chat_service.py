from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Iterator

from app.core.config import settings
from app.llm.client import get_chat_model
from app.llm.prompts import (
    advice_answer_prompt,
    chat_answer_prompt,
    chat_intent_prompt,
    react_step_prompt,
    react_synthesis_prompt,
    search_answer_prompt,
)
from app.rag.retriever import ContractKnowledgeRetriever
from app.rag.vector_store import load_vector_store
from app.schemas.chat import ChatRequest, ChatResponse, ChatSearchResult
from app.schemas.review import ReviewRequest
from app.services.react_runtime import (
    ActionContext,
    ActionReference,
    ActionRegistry,
    QueryKnowledgeAction,
    ReactTraceStep,
    references_to_search_results,
)
from app.services.review_service import ReviewService


# Dedicated trace logger: writes ReAct reasoning traces to a separate file
_trace_logger = logging.getLogger("chat_trace")
_trace_handler = logging.FileHandler(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".run", "chat_trace.log"),
    encoding="utf-8",
    delay=True,
)
_trace_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
_trace_logger.addHandler(_trace_handler)
_trace_logger.setLevel(logging.INFO)
_trace_logger.propagate = False


class ChatService:
    STREAM_MAX_SECONDS = 24.0
    STREAM_MAX_CHARS = 900

    def __init__(self) -> None:
        self.review_service = ReviewService()
        self.llm = None
        self._knowledge_retriever = None
        self._action_registry = ActionRegistry()
        self._action_registry.register(QueryKnowledgeAction(self._require_knowledge_retriever))

    def chat(self, payload: ChatRequest) -> ChatResponse:
        final_payload: dict[str, Any] | None = None
        for event in self.chat_stream(payload):
            if event.get("event") == "done":
                final_payload = event.get("data")
        if final_payload is None:
            raise RuntimeError("聊天流程未返回最终结果。")
        return ChatResponse.model_validate(final_payload)

    def chat_stream(self, payload: ChatRequest) -> Iterator[dict[str, Any]]:
        intent_payload = self._route_intent(payload)
        intent = intent_payload.get("intent", "chat")
        query = intent_payload.get("query") or self._latest_user_message(payload)

        if intent == "review":
            response = self._handle_review(payload, query)
            yield {"event": "start", "data": {"intent": response.intent, "tool_used": response.tool_used}}
            for delta in self._chunk_text(response.answer):
                yield {"event": "delta", "data": {"delta": delta}}
            yield {"event": "done", "data": response.model_dump(mode="json")}
            return

        for event in self._handle_react_stream(payload, intent=intent, query=query):
            yield event

    def _handle_review(self, payload: ChatRequest, query: str) -> ChatResponse:
        contract_text = self._resolve_contract_text(payload)
        if not contract_text:
            return ChatResponse(
                intent="review",
                tool_used="review_guardrail",
                answer="我理解你想做合同审查，但当前对话里还没有可用于校审的合同正文。请先粘贴合同全文，或在左侧文本区填写后再发起对话。",
                generated_at=datetime.now(timezone.utc),
            )

        review_result = self.review_service.review(
            ReviewRequest(
                contract_text=contract_text,
                contract_type=payload.contract_type,
                our_side=payload.our_side,
            )
        )
        summary = review_result.summary
        answer = (
            f"我已经调用合同审查工具完成校审。当前识别到 {summary.risk_count} 项风险，"
            f"整体风险等级为 {summary.overall_risk}。你可以继续追问具体条款、某项风险，或者让我基于结果给修改建议。"
        )
        return ChatResponse(
            intent="review",
            tool_used="review",
            answer=answer,
            generated_at=datetime.now(timezone.utc),
            review_result=review_result,
        )

    def _handle_react_stream(self, payload: ChatRequest, intent: str, query: str) -> Iterator[dict[str, Any]]:
        llm = self._require_llm()
        max_steps = max(1, settings.react_max_steps)
        action_context = ActionContext(
            user_message=self._latest_user_message(payload),
            intent=intent,
            conversation=self._conversation_text(payload),
        )

        trace_steps: list[ReactTraceStep] = []
        collected_references: list[ActionReference] = []
        latest_observation = "暂无观察"
        final_answer = ""
        used_action = False

        yield {
            "event": "start",
            "data": {
                "intent": intent,
                "tool_used": "react",
                "actions": self._action_registry.manifest(),
            },
        }

        for step in range(1, max_steps + 1):
            plan = self._plan_react_step(
                llm=llm,
                payload=payload,
                intent=intent,
                query=query,
                latest_observation=latest_observation,
                trace_steps=trace_steps,
            )

            thought = str(plan.get("thought_summary") or "").strip() or f"继续分析第 {step} 步。"
            action = str(plan.get("action") or "").strip() or "finish"
            action_input = plan.get("action_input") if isinstance(plan.get("action_input"), dict) else {}
            if action == "query_knowledge" and not action_input.get("query"):
                action_input = {"query": query}
            final_answer_candidate = str(plan.get("final_answer") or "").strip()

            _trace_logger.info("STEP=%d | THOUGHT=%s | ACTION=%s | INPUT=%s", step, thought, action, json.dumps(action_input, ensure_ascii=False))
            yield {"event": "reasoning", "data": {"step": step, "summary": thought}}

            if action == "finish":
                observation = "规划器判断信息已充分，进入最终回答。"
                trace_steps.append(ReactTraceStep(step=step, thought=thought, action="finish", observation=observation))
                final_answer = final_answer_candidate
                break

            yield {
                "event": "action",
                "data": {
                    "step": step,
                    "name": action,
                    "input_preview": action_input,
                },
            }
            used_action = True

            result = self._action_registry.execute(action, action_context, action_input)
            collected_references.extend(result.references)
            latest_observation = result.summary
            trace_steps.append(ReactTraceStep(step=step, thought=thought, action=action, observation=result.summary))
            yield {
                "event": "observation",
                "data": {
                    "step": step,
                    "action": action,
                    "success": result.success,
                    "summary": result.summary,
                    "refs": [item.model_dump(mode="json") for item in references_to_search_results(result.references)],
                    "error_code": result.error_code,
                    "retryable": result.retryable,
                    "failure_type": result.metadata.get("failure_type"),
                },
            }

        if not final_answer:
            final_answer = self._synthesize_react_answer(
                llm=llm,
                payload=payload,
                intent=intent,
                trace_steps=trace_steps,
                references=collected_references,
            )

        # Log ReAct trace to dedicated file for post-hoc review
        _trace_logger.info(
            "INTENT=%s | QUERY=%s | TRACE=%s",
            intent,
            query[:120],
            json.dumps([s.to_summary_dict() for s in trace_steps], ensure_ascii=False),
        )

        answer = ""
        stream_started_at = time.monotonic()
        hit_limit = False
        for delta in self._chunk_text(final_answer):
            if time.monotonic() - stream_started_at >= self.STREAM_MAX_SECONDS or len(answer) >= self.STREAM_MAX_CHARS:
                hit_limit = True
                break
            answer += delta
            yield {"event": "delta", "data": {"delta": delta}}

        if hit_limit:
            tail = "\n\n（已先返回核心结论；如需展开细节请继续追问。）"
            answer += tail
            yield {"event": "delta", "data": {"delta": tail}}

        response = ChatResponse(
            intent=intent if intent in {"search", "advice", "chat"} else "chat",
            tool_used="react_query_knowledge" if used_action else "react",
            answer=answer,
            generated_at=datetime.now(timezone.utc),
            search_results=references_to_search_results(self._dedupe_references(collected_references)),
            trace_summary=[step.to_summary_dict() for step in trace_steps],
        )
        yield {"event": "done", "data": response.model_dump(mode="json")}

    def _plan_react_step(
        self,
        llm: Any,
        payload: ChatRequest,
        intent: str,
        query: str,
        latest_observation: str,
        trace_steps: list[ReactTraceStep],
    ) -> dict[str, Any]:
        raw = self._invoke_chain_once(
            react_step_prompt | llm,
            {
                "intent": intent,
                "user_message": query,
                "conversation": self._conversation_text(payload),
                "latest_observation": latest_observation,
                "trace_history": self._format_trace_history_for_prompt(trace_steps),
            },
        )
        return self._parse_react_step_output(raw, default_query=query)

    def _synthesize_react_answer(
        self,
        llm: Any,
        payload: ChatRequest,
        intent: str,
        trace_steps: list[ReactTraceStep],
        references: list[ActionReference],
    ) -> str:
        return self._invoke_chain_once(
            react_synthesis_prompt | llm,
            {
                "intent": intent,
                "user_message": self._latest_user_message(payload),
                "conversation": self._conversation_text(payload),
                "trace_history": self._format_trace_history_for_prompt(trace_steps),
                "retrieved_context": self._format_retrieved_context(references),
            },
        )

    def _handle_search(self, payload: ChatRequest, query: str) -> ChatResponse:
        retriever = self._require_knowledge_retriever()
        llm = self._require_llm()
        docs = retriever.retrieve_documents(query=query, k=3)
        contexts = [doc.page_content for doc in docs]
        answer = self._invoke_chain_once(
            search_answer_prompt | llm,
            {
                "user_message": self._latest_user_message(payload),
                "retrieved_context": "\n\n".join(contexts) if contexts else "未检索到相关内容",
            },
        )
        return ChatResponse(
            intent="search",
            tool_used="knowledge_search",
            answer=answer,
            generated_at=datetime.now(timezone.utc),
            search_results=self._to_search_results(docs),
        )

    def _handle_advice(self, payload: ChatRequest, query: str) -> ChatResponse:
        retriever = self._require_knowledge_retriever()
        llm = self._require_llm()
        docs = retriever.retrieve_documents(query=query, k=3)
        contexts = [doc.page_content for doc in docs]
        answer = self._invoke_chain_once(
            advice_answer_prompt | llm,
            {
                "user_message": self._latest_user_message(payload),
                "contract_text": payload.contract_text or "无合同上下文",
                "retrieved_context": "\n\n".join(contexts) if contexts else "未检索到相关内容",
            },
        )
        return ChatResponse(
            intent="advice",
            tool_used="advice",
            answer=answer,
            generated_at=datetime.now(timezone.utc),
            search_results=self._to_search_results(docs),
        )

    def _handle_chat(self, payload: ChatRequest) -> ChatResponse:
        llm = self._require_llm()
        answer = self._invoke_chain_once(
            chat_answer_prompt | llm,
            {
                "conversation": self._conversation_text(payload),
                "user_message": self._latest_user_message(payload),
            },
        )
        return ChatResponse(
            intent="chat",
            tool_used="chat",
            answer=answer,
            generated_at=datetime.now(timezone.utc),
        )

    def _route_intent(self, payload: ChatRequest) -> dict[str, Any]:
        llm = self._require_llm()
        raw = self._invoke_chain_once(
            chat_intent_prompt | llm,
            {
                "contract_text": payload.contract_text or "无合同上下文",
                "conversation": self._conversation_text(payload),
            },
        )
        return self._parse_router_output(raw, payload)

    def _parse_router_output(self, raw: str, payload: ChatRequest) -> dict[str, Any]:
        match = re.search(r"\{.*\}", raw, re.S)
        latest = self._latest_user_message(payload)
        if match:
            try:
                data = json.loads(match.group(0))
                intent = data.get("intent")
                if intent in {"search", "review", "advice", "chat"}:
                    if intent == "review" and not self._is_explicit_review_request(latest):
                        return {
                            "intent": "advice",
                            "query": data.get("query") or latest,
                            "reason": "review-downgraded-to-advice",
                        }
                    return data
            except json.JSONDecodeError:
                import logging
                logging.getLogger(__name__).warning(
                    "LLM router returned malformed JSON, falling back to keyword routing. Raw output: %s", raw
                )

        if self._is_explicit_review_request(latest):
            return {"intent": "review", "query": latest, "reason": "fallback-review"}
        if any(keyword in latest for keyword in ("法条", "依据", "搜索", "检索", "查询")):
            return {"intent": "search", "query": latest, "reason": "fallback-search"}
        if any(keyword in latest for keyword in ("建议", "怎么改", "如何写", "怎么写", "风险", "解释", "说明")):
            return {"intent": "advice", "query": latest, "reason": "fallback-advice"}
        return {"intent": "chat", "query": latest, "reason": "fallback-chat"}

    def _parse_react_step_output(self, raw: str, default_query: str) -> dict[str, Any]:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return {"thought_summary": "无法解析规划输出，直接给出结论。", "action": "finish", "final_answer": ""}
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {"thought_summary": "规划输出非 JSON，直接给出结论。", "action": "finish", "final_answer": ""}

        action = str(data.get("action") or "").strip()
        if action not in {"query_knowledge", "finish"}:
            action = "finish"
        action_input = data.get("action_input")
        if not isinstance(action_input, dict):
            action_input = {}
        if action == "query_knowledge" and not action_input.get("query"):
            action_input = {"query": default_query}

        return {
            "thought_summary": str(data.get("thought_summary") or "").strip(),
            "action": action,
            "action_input": action_input,
            "final_answer": str(data.get("final_answer") or "").strip(),
        }

    def _format_trace_history_for_prompt(self, trace_steps: list[ReactTraceStep]) -> str:
        if not trace_steps:
            return "暂无轨迹。"
        return "\n".join(
            f"Step {item.step}: thought={item.thought}; action={item.action}; observation={item.observation}"
            for item in trace_steps
        )

    def _format_retrieved_context(self, references: list[ActionReference]) -> str:
        if not references:
            return "未检索到相关内容"
        rows = []
        for index, ref in enumerate(references[:6], start=1):
            rows.append(
                f"[{index}] {ref.source_title}"
                + (f" ({ref.article_label})" if ref.article_label else "")
                + f"\n{ref.snippet}"
            )
        return "\n\n".join(rows)

    def _invoke_chain_once(self, chain: Any, chain_input: dict[str, Any]) -> str:
        output = chain.invoke(chain_input)
        return self._chunk_to_text(output)

    def _stream_chain_response(self, chain: Any, chain_input: dict[str, Any]) -> Iterator[str]:
        for chunk in chain.stream(chain_input):
            content = self._chunk_to_text(chunk)
            if content:
                yield content

    def _require_llm(self):
        if not settings.qwen_api_key:
            raise RuntimeError("QWEN_API_KEY 未配置，无法启用对话功能。")
        if self.llm is None:
            try:
                self.llm = get_chat_model()
            except Exception as exc:
                raise RuntimeError(f"聊天模型初始化失败：{exc}") from exc
        return self.llm

    def _require_knowledge_retriever(self) -> ContractKnowledgeRetriever:
        if self._knowledge_retriever is None:
            try:
                vector_store = load_vector_store(settings.knowledge_vector_store_dir)
            except Exception as exc:
                raise RuntimeError(f"法律知识库加载失败：{exc}") from exc
            self._knowledge_retriever = ContractKnowledgeRetriever(vector_store)
        return self._knowledge_retriever

    def _latest_user_message(self, payload: ChatRequest) -> str:
        for message in reversed(payload.messages):
            if message.role == "user":
                return message.content
        return payload.messages[-1].content

    def _conversation_text(self, payload: ChatRequest) -> str:
        return "\n".join(f"{message.role}: {message.content}" for message in payload.messages)

    def _resolve_contract_text(self, payload: ChatRequest) -> str | None:
        if payload.contract_text:
            return payload.contract_text
        latest = self._latest_user_message(payload)
        if len(latest) > 100 and any(keyword in latest for keyword in ("甲方", "乙方", "第一条", "合同")):
            return latest
        return None

    def _to_search_results(self, docs: list[Any]) -> list[ChatSearchResult]:
        return [
            ChatSearchResult(
                source_title=doc.metadata.get("title") or doc.metadata.get("doc_name") or "未命名知识片段",
                article_label=doc.metadata.get("article_label"),
                snippet=(doc.page_content or "")[:240],
                source_path=doc.metadata.get("source_path"),
            )
            for doc in docs
        ]

    def _dedupe_references(self, references: list[ActionReference]) -> list[ActionReference]:
        deduped: list[ActionReference] = []
        seen: set[tuple[str, str, str | None]] = set()
        for ref in references:
            key = (ref.source_title, ref.snippet, ref.source_path)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(ref)
        return deduped

    def _is_explicit_review_request(self, text: str) -> bool:
        return any(
            keyword in text
            for keyword in (
                "审查",
                "校审",
                "审阅",
                "重新扫描",
                "扫描合同",
                "复核",
                "检查合同",
                "跑一遍审查",
            )
        )

    def _chunk_to_text(self, chunk: Any) -> str:
        if chunk is None:
            return ""
        if isinstance(chunk, str):
            return chunk
        content = getattr(chunk, "content", None)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
                else:
                    text = getattr(item, "text", None)
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return str(content or "")

    def _chunk_text(self, text: str, chunk_size: int = 32) -> Iterator[str]:
        if not text:
            return
        for i in range(0, len(text), chunk_size):
            yield text[i : i + chunk_size]
