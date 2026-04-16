from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from app.core.config import settings
from app.llm.client import get_chat_model
from app.llm.prompts import advice_answer_prompt, chat_answer_prompt, chat_intent_prompt, search_answer_prompt
from app.rag.retriever import ContractKnowledgeRetriever
from app.rag.vector_store import load_vector_store
from app.schemas.chat import ChatRequest, ChatResponse, ChatSearchResult
from app.schemas.review import ReviewRequest
from app.services.review_service import ReviewService


class ChatService:
    def __init__(self) -> None:
        self.review_service = ReviewService()
        self.llm = None
        self._knowledge_retriever = None

    def chat(self, payload: ChatRequest) -> ChatResponse:
        intent_payload = self._route_intent(payload)
        intent = intent_payload.get("intent", "chat")
        query = intent_payload.get("query") or self._latest_user_message(payload)

        if intent == "review":
            return self._handle_review(payload, query)
        if intent == "search":
            return self._handle_search(payload, query)
        if intent == "advice":
            return self._handle_advice(payload, query)
        return self._handle_chat(payload)

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
                    return data
            except json.JSONDecodeError:
                pass

        if any(keyword in latest for keyword in ("审查", "校审", "审阅", "风险")):
            return {"intent": "review", "query": latest, "reason": "fallback-review"}
        if any(keyword in latest for keyword in ("法条", "依据", "搜索", "检索", "查询")):
            return {"intent": "search", "query": latest, "reason": "fallback-search"}
        if any(keyword in latest for keyword in ("建议", "怎么改", "如何写", "怎么写")):
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
