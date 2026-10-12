from typing import Literal
from pydantic import BaseModel, Field


class IntentClassificationOutput(BaseModel):
    intent: Literal[
        "query_order",
        "refund",
        "logistics",
        "product_question",
        "human_service",
        "other",
    ]
    confidence: float = Field(..., ge=0, le=1)
    need_order_id: bool = False
    reply_strategy: Literal[
        "answer_directly", "ask_order_id", "call_tool", "transfer_human", "reject"
    ]
    reason: str


class RAGStructuredAnswerOutput(BaseModel):
    answer: str
    is_answered: bool
    citations: list[str] = []
    missing_info: str | None = None
    confidence: float = 0


class AgentPlanStep(BaseModel):
    step_id: int
    name: str
    action_type: Literal["think", "tool_call", "respond"]
    tool_name: str | None = None
    arguments: dict = {}
    reason: str


class AgentPlanOutput(BaseModel):
    goal: str
    need_tools: bool
    steps: list[AgentPlanStep]
    final_response_style: str = "short"
