from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class LLMRole(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


class LLMToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    raw_arguments: str = "{}"


class LLMMessage(BaseModel):
    role: LLMRole
    content: str = ""
    tool_call_id: str | None = None
    tool_calls: list[LLMToolCall] | None = None


class LLMUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMRequest(BaseModel):
    model: str
    messages: list[LLMMessage]
    temperature: float = 0.7
    stream: bool = False
    response_format: dict | None = None
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None


class LLMResponse(BaseModel):
    provider: str
    model: str
    content: str = ""
    usage: LLMUsage = Field(default_factory=LLMUsage)
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    finish_reason: str | None = None


class LLMStreamChunk(BaseModel):
    provider: str
    model: str
    content: str = ""
    usage: LLMUsage | None = None
    finish_reason: str | None = None
