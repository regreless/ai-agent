from src.llm.schemas import LLMMessage, LLMRequest, LLMRole
from src.llm.provider import BaseLLMProvider
from src.structured_outputs.parser import parse_structured_output
from src.structured_outputs.schemas import (
    IntentClassificationOutput,
    RAGStructuredAnswerOutput,
    AgentPlanOutput,
)


async def classify_intent(
    question: str, model: str, llm: BaseLLMProvider
) -> IntentClassificationOutput:
    response = await llm.chat(
        LLMRequest(
            model=model,
            messages=[
                LLMMessage(role=LLMRole.system, content="识别用户意图，只输出 JSON。"),
                LLMMessage(role=LLMRole.user, content=question),
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
    )
    return parse_structured_output(response.content, IntentClassificationOutput)


async def rag_answer(
    question: str, context: str, model: str, llm: BaseLLMProvider
) -> RAGStructuredAnswerOutput:
    response = await llm.chat(
        LLMRequest(
            model=model,
            messages=[
                LLMMessage(
                    role=LLMRole.system, content="RAG 知识库结构化回答，只输出 JSON。"
                ),
                LLMMessage(
                    role=LLMRole.user, content=question + "\n知识库：" + context
                ),
            ],
            response_format={"type": "json_object"},
        )
    )
    return parse_structured_output(response.content, RAGStructuredAnswerOutput)


async def agent_plan(
    goal: str, tools: str, constraints: str, model: str, llm: BaseLLMProvider
) -> AgentPlanOutput:
    response = await llm.chat(
        LLMRequest(
            model=model,
            messages=[
                LLMMessage(
                    role=LLMRole.system, content="Agent 任务规划，只输出 JSON。"
                ),
                LLMMessage(
                    role=LLMRole.user,
                    content=goal + "\n工具：" + tools + "\n约束：" + constraints,
                ),
            ],
            response_format={"type": "json_object"},
        )
    )
    return parse_structured_output(response.content, AgentPlanOutput)
