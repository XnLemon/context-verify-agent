from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from app.rag.retriever import ContractKnowledgeRetriever
from app.schemas.chat import ChatSearchResult


@dataclass
class ActionReference:
    source_title: str
    snippet: str
    source_path: str | None = None
    article_label: str | None = None


@dataclass
class ActionResult:
    success: bool
    summary: str
    references: list[ActionReference] = field(default_factory=list)
    error_code: str | None = None
    retryable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionContext:
    user_message: str
    intent: str
    conversation: str


class ActionHandler(Protocol):
    name: str
    description: str
    input_schema: dict[str, Any]

    def execute(self, context: ActionContext, args: dict[str, Any]) -> ActionResult:
        ...


class ActionRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, ActionHandler] = {}

    def register(self, handler: ActionHandler) -> None:
        self._handlers[handler.name] = handler

    def get(self, name: str) -> ActionHandler | None:
        return self._handlers.get(name)

    def manifest(self) -> list[dict[str, Any]]:
        # MCP-style metadata contract for discoverable, extensible actions.
        return [
            {
                "name": handler.name,
                "description": handler.description,
                "input_schema": handler.input_schema,
            }
            for handler in self._handlers.values()
        ]

    def execute(self, name: str, context: ActionContext, args: dict[str, Any]) -> ActionResult:
        handler = self.get(name)
        if handler is None:
            return ActionResult(
                success=False,
                summary=f"未找到动作：{name}",
                error_code="action_not_found",
                metadata={"failure_type": "action_registry"},
            )
        return handler.execute(context, args)


class QueryKnowledgeAction:
    name = "query_knowledge"
    description = "检索合同相关法律知识片段，用于依据型问题回答。"
    input_schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }

    def __init__(self, retriever_provider: Callable[[], ContractKnowledgeRetriever]) -> None:
        self._retriever_provider = retriever_provider

    def execute(self, context: ActionContext, args: dict[str, Any]) -> ActionResult:
        query = str((args or {}).get("query") or "").strip()
        if not query:
            return ActionResult(
                success=False,
                summary="query_knowledge 参数缺失：query 不能为空。",
                error_code="invalid_action_args",
                metadata={"failure_type": "validation"},
            )
        try:
            docs = self._retriever_provider().retrieve_documents(query=query, k=3)
        except Exception as exc:  # pragma: no cover - runtime dependency failures
            return ActionResult(
                success=False,
                summary=f"知识检索失败：{exc}",
                error_code="knowledge_search_failed",
                retryable=True,
                metadata={"failure_type": "runtime_exception"},
            )

        references = [
            ActionReference(
                source_title=doc.metadata.get("title") or doc.metadata.get("doc_name") or "未命名知识片段",
                article_label=doc.metadata.get("article_label"),
                snippet=(doc.page_content or "")[:240],
                source_path=doc.metadata.get("source_path"),
            )
            for doc in docs
        ]
        if not references:
            return ActionResult(
                success=True,
                summary="未检索到直接相关的外部知识片段。",
                references=[],
            )
        return ActionResult(
            success=True,
            summary=f"命中 {len(references)} 条知识片段，可用于依据回答。",
            references=references,
        )


@dataclass
class ReactTraceStep:
    step: int
    thought: str
    action: str
    observation: str

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "thought": self.thought,
            "action": self.action,
            "observation": self.observation,
        }


def references_to_search_results(references: list[ActionReference]) -> list[ChatSearchResult]:
    return [
        ChatSearchResult(
            source_title=ref.source_title,
            article_label=ref.article_label,
            snippet=ref.snippet,
            source_path=ref.source_path,
        )
        for ref in references
    ]
