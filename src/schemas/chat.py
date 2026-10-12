from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str = Field(..., min_length=1)


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    model: str = "mock-chat"
    temperature: float = 0.7
    stream: bool = False
    session_id: str | None = None
    user_id: str | None = None
    prompt_scenario: str | None = "general_chat"
    prompt_version: str | None = "v1"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    answer: str
    model: str
    session_id: str | None = None
    message_id: str | None = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    sources: list[dict] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)


class ConversationResponse(BaseModel):
    conversation_id: str
    title: str
    status: str
    created_at: str | None = None
    updated_at: str | None = None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]


class ConversationMessagesResponse(BaseModel):
    conversation_id: str
    messages: list[ChatMessage]
