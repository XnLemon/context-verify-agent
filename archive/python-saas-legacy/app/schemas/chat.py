from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.review import ReviewResponse


ChatRole = Literal["system", "user", "assistant"]
ChatIntent = Literal["search", "review", "advice", "chat"]


class ChatMessage(BaseModel):
    role: ChatRole
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    contract_text: str | None = Field(default=None, description="可选的合同全文，用于审查或上下文理解")
    contract_type: str | None = None
    our_side: str = Field(default="甲方")


class ChatSearchResult(BaseModel):
    source_title: str
    article_label: str | None = None
    snippet: str
    source_path: str | None = None


class ChatResponse(BaseModel):
    intent: ChatIntent
    tool_used: str
    answer: str
    generated_at: datetime
    search_results: list[ChatSearchResult] = Field(default_factory=list)
    review_result: ReviewResponse | None = None
