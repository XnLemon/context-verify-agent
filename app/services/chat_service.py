from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Iterator

from app.core.config import settings
from app.llm.client import get_chat_model
from app.llm.prompts import advice_answer_prompt, chat_answer_prompt, chat_intent_prompt, search_answer_prompt
from app.rag.retriever import ContractKnowledgeRetriever
from app.rag.vector_store import load_vector_store
from app.schemas.chat import ChatRequest, ChatResponse, ChatSearchResult
from app.schemas.review import ReviewRequest
from app.services.review_service import ReviewService


class ChatService:
    STREAM_MAX_SECONDS = 24.0
    STREAM_MAX_CHARS = 900

    def __init__(self) -> None:
        self.review_service = ReviewService()
        self.llm = None
        self._knowledge_retriever = None

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

        if intent == "search":
            response = self._handle_search_stream(payload, query)
            for event in response:
                yield event
            return

        if intent == "advice":
            response = self._handle_advice_stream(payload, query)
            for event in response:
                yield event
            return

        response = self._handle_chat_stream(payload)
        for event in response:
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

    def _handle_search(self, payload: ChatRequest, query: str) -> ChatResponse:
        retriever = self._require_knowledge_retriever()
        llm = self._require_llm()
        docs = retriever.retrieve_documents(query=query, k=3)
        contexts = [doc.page_content for doc in docs]
        answer = (search_answer_prompt | llm).invoke(
            {
                "user_message": self._latest_user_message(payload),
                "retrieved_context": "\n\n".join(contexts) if contexts else "未检索到相关内容",
            }
        ).content
        return ChatResponse(
            intent="search",
            tool_used="knowledge_search",
            answer=answer,
            generated_at=datetime.now(timezone.utc),
            search_results=self._to_search_results(docs),
        )

    def _handle_search_stream(self, payload: ChatRequest, query: str) -> Iterator[dict[str, Any]]:
        retriever = self._require_knowledge_retriever()
        llm = self._require_llm()
        docs = retriever.retrieve_documents(query=query, k=3)
        contexts = [doc.page_content for doc in docs]
        yield {"event": "start", "data": {"intent": "search", "tool_used": "knowledge_search"}}

        answer = ""
        stream_started_at = time.monotonic()
        hit_limit = False
        for delta in self._stream_chain_response(
            search_answer_prompt | llm,
            {
                "user_message": self._latest_user_message(payload),
                "retrieved_context": "\n\n".join(contexts) if contexts else "未检索到相关内容",
            },
        ):
            if time.monotonic() - stream_started_at >= self.STREAM_MAX_SECONDS or len(answer) >= self.STREAM_MAX_CHARS:
                hit_limit = True
                break
            answer += delta
            yield {"event": "delta", "data": {"delta": delta}}

        if hit_limit:
            tail = "\n\n（已先返回核心结论；如需展开细节，请继续追问具体条款）"
            answer += tail
            yield {"event": "delta", "data": {"delta": tail}}

        response = ChatResponse(
            intent="search",
            tool_used="knowledge_search",
            answer=answer,
            generated_at=datetime.now(timezone.utc),
            search_results=self._to_search_results(docs),
        )
        yield {"event": "done", "data": response.model_dump(mode="json")}

    def _handle_advice(self, payload: ChatRequest, query: str) -> ChatResponse:
        retriever = self._require_knowledge_retriever()
        llm = self._require_llm()
        docs = retriever.retrieve_documents(query=query, k=3)
        contexts = [doc.page_content for doc in docs]
        answer = (advice_answer_prompt | llm).invoke(
            {
                "user_message": self._latest_user_message(payload),
                "contract_text": payload.contract_text or "无合同上下文",
                "retrieved_context": "\n\n".join(contexts) if contexts else "未检索到相关内容",
            }
        ).content
        return ChatResponse(
            intent="advice",
            tool_used="advice",
            answer=answer,
            generated_at=datetime.now(timezone.utc),
            search_results=self._to_search_results(docs),
        )

    def _handle_advice_stream(self, payload: ChatRequest, query: str) -> Iterator[dict[str, Any]]:
        retriever = self._require_knowledge_retriever()
        llm = self._require_llm()
        docs = retriever.retrieve_documents(query=query, k=3)
        contexts = [doc.page_content for doc in docs]
        yield {"event": "start", "data": {"intent": "advice", "tool_used": "advice"}}

        answer = ""
        stream_started_at = time.monotonic()
        hit_limit = False
        for delta in self._stream_chain_response(
            advice_answer_prompt | llm,
            {
                "user_message": self._latest_user_message(payload),
                "contract_text": payload.contract_text or "无合同上下文",
                "retrieved_context": "\n\n".join(contexts) if contexts else "未检索到相关内容",
            },
        ):
            if time.monotonic() - stream_started_at >= self.STREAM_MAX_SECONDS or len(answer) >= self.STREAM_MAX_CHARS:
                hit_limit = True
                break
            answer += delta
            yield {"event": "delta", "data": {"delta": delta}}

        if hit_limit:
            tail = "\n\n（已先返回核心建议；如需某一条款的完整改写，请直接指出条款）"
            answer += tail
            yield {"event": "delta", "data": {"delta": tail}}

        response = ChatResponse(
            intent="advice",
            tool_used="advice",
            answer=answer,
            generated_at=datetime.now(timezone.utc),
            search_results=self._to_search_results(docs),
        )
        yield {"event": "done", "data": response.model_dump(mode="json")}

    def _handle_chat(self, payload: ChatRequest) -> ChatResponse:
        llm = self._require_llm()
        answer = (chat_answer_prompt | llm).invoke(
            {
                "conversation": self._conversation_text(payload),
                "user_message": self._latest_user_message(payload),
            }
        ).content
        return ChatResponse(
            intent="chat",
            tool_used="chat",
            answer=answer,
            generated_at=datetime.now(timezone.utc),
        )

    def _handle_chat_stream(self, payload: ChatRequest) -> Iterator[dict[str, Any]]:
        llm = self._require_llm()
        yield {"event": "start", "data": {"intent": "chat", "tool_used": "chat"}}

        answer = ""
        stream_started_at = time.monotonic()
        hit_limit = False
        for delta in self._stream_chain_response(
            chat_answer_prompt | llm,
            {
                "conversation": self._conversation_text(payload),
                "user_message": self._latest_user_message(payload),
            },
        ):
            if time.monotonic() - stream_started_at >= self.STREAM_MAX_SECONDS or len(answer) >= self.STREAM_MAX_CHARS:
                hit_limit = True
                break
            answer += delta
            yield {"event": "delta", "data": {"delta": delta}}

        if hit_limit:
            tail = "\n\n（为保证时效，已先返回核心内容；你可以继续追问某个点）"
            answer += tail
            yield {"event": "delta", "data": {"delta": tail}}

        response = ChatResponse(
            intent="chat",
            tool_used="chat",
            answer=answer,
            generated_at=datetime.now(timezone.utc),
        )
        yield {"event": "done", "data": response.model_dump(mode="json")}

    def _route_intent(self, payload: ChatRequest) -> dict:
        llm = self._require_llm()
        raw = (chat_intent_prompt | llm).invoke(
            {
                "contract_text": payload.contract_text or "无合同上下文",
                "conversation": self._conversation_text(payload),
            }
        ).content
        return self._parse_router_output(raw, payload)

    def _parse_router_output(self, raw: str, payload: ChatRequest) -> dict:
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
                pass

        if self._is_explicit_review_request(latest):
            return {"intent": "review", "query": latest, "reason": "fallback-review"}
        if any(keyword in latest for keyword in ("法条", "依据", "搜索", "检索", "查询")):
            return {"intent": "search", "query": latest, "reason": "fallback-search"}
        if any(keyword in latest for keyword in ("建议", "怎么改", "如何写", "怎么写", "风险", "解释", "说明")):
            return {"intent": "advice", "query": latest, "reason": "fallback-advice"}
        return {"intent": "chat", "query": latest, "reason": "fallback-chat"}

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

    def _to_search_results(self, docs) -> list[ChatSearchResult]:
        return [
            ChatSearchResult(
                source_title=doc.metadata.get("title") or doc.metadata.get("doc_name") or "未命名知识片段",
                article_label=doc.metadata.get("article_label"),
                snippet=doc.page_content[:240],
                source_path=doc.metadata.get("source_path"),
            )
            for doc in docs
        ]

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

    def _stream_chain_response(self, chain, chain_input: dict[str, Any]) -> Iterator[str]:
        for chunk in chain.stream(chain_input):
            content = self._chunk_to_text(chunk)
            if content:
                yield content

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
