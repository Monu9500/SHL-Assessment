from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(default="", max_length=20000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list, min_length=1)


class RecommendationItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., min_length=8, max_length=2048)
    test_type: str = Field(default="", max_length=32)


class ChatResponse(BaseModel):
    reply: str = Field(default="", max_length=20000)
    recommendations: list[RecommendationItem]
    end_of_conversation: bool = False


class ParsedAgentDecision(BaseModel):
    """Intermediate structure produced by LLM parsing (validated server-side)."""

    mode: Literal["clarify", "recommend", "refuse", "compare"] = "clarify"
    reply: str = ""
    end_of_conversation: bool = False
    selected_indices: list[int] = Field(default_factory=list)
