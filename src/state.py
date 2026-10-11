from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class AgentStepType(str, Enum):
    THINK = "think"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FINAL = "final"


class AgentStep(BaseModel):
    step_type: AgentStepType = Field(..., description="步骤类型")
    content: str = Field(..., description="步骤内容")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展信息")


class AgentState(BaseModel):
    user_id: str = Field(..., description="用户 ID")
    session_id: str = Field(..., description="会话 ID")
    question: str = Field(..., min_length=1, description="用户问题")
    steps: list[AgentStep] = Field(default_factory=list, description="Agent 执行步骤")
    final_answer: str | None = Field(default=None, description="最终答案")


state = AgentState(
    user_id="u_10001",
    session_id="s_10001",
    question="帮我查询订单 10001 的物流状态"
)

state.steps.append(
    AgentStep(
        step_type=AgentStepType.THINK,
        content="用户想查询订单物流，需要调用 query_logistics 工具"
    )
)

state.steps.append(
    AgentStep(
        step_type=AgentStepType.TOOL_CALL,
        content="调用 query_logistics",
        metadata={
            "order_id": "10001"
        }
    )
)

state.final_answer = "订单 10001 当前正在运输中，预计明天送达。"

print(state.model_dump())
