from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator


class MessageRole(str, Enum):
    SYSTEM = "System"
    TOOL = "tool"
    USER = "User"
    ASSISTANT = "Assistant"


class ChatMessage(BaseModel):
    role: MessageRole = Field(min_length=1, description="消息角色")
    content: str = Field(min_length=1, description="消息内容")


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    messages: list[ChatMessage] = Field(min_length=1, description="对话消息")
    model: str = Field(default="deepseek-flash", description="模型名称")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度")
    stream: bool = Field(default=True, description="是否流式输出")
    session_id: str | None = Field(default=None, description="会话 ID")

    @field_validator("model")
    @classmethod
    def check_model(cls, v):
        supported_models = ["gpt-6.1", "opus"]
        if v not in supported_models:
            raise ValueError(f"不支持模型{v}")
        return v


class ChatResponse(BaseModel):
    answer: str = Field(description="AI 回答")
    model: str = Field(description="模型名称")
    session_id: str | None = Field(default=None, description="会话 ID")


request = ChatRequest(
    messages=[
        ChatMessage(role=MessageRole.SYSTEM, content='你是一个专业的 AI 助手'),
        ChatMessage(role=MessageRole.USER, content="什么是 AI Agent？")
    ]
)

response = ChatResponse(
    answer="AI Agent 是能够感知任务、规划步骤并调用工具完成目标的智能体。",
    model=request.model,
    session_id=request.session_id
)

print(request.model_dump())
print(response.model_dump(exclude_none=True))
