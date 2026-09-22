"""安全、性能、规范三个审查任务并行执行。"""

import operator
from time import perf_counter
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field

from app.config import llm

REVIEW_TASKS = {
    "安全性": "检查 SQL 注入、XSS、敏感信息泄露等安全问题。",
    "性能": "检查算法复杂度、N+1 查询、内存泄漏等性能问题。",
    "代码规范": "检查命名、注释、重复代码和错误处理。",
}


class ReviewResult(BaseModel):
    issues: list[str]
    score: float = Field(ge=0, le=10, allow_inf_nan=False)


class ReviewState(TypedDict):
    code: str
    language: str
    review_results: Annotated[list[dict], operator.add]
    report: str


class SingleReviewState(TypedDict):
    code: str
    language: str
    aspect: str
    prompt: str


def dispatch_reviews(state: ReviewState):
    return [Send("review_agent", {"code": state["code"], "language": state["language"],
                                  "aspect": aspect, "prompt": prompt})
            for aspect, prompt in REVIEW_TASKS.items()]


async def review_agent(state: SingleReviewState):
    response = await llm.ainvoke([HumanMessage(content=
        f"{state['prompt']}\n只输出 JSON：{{\"issues\":[\"问题描述\"],\"score\":7}}，评分范围 0-10。"
        f"\n{state['language']} 代码：\n```\n{state['code']}\n```"
    )])
    try:
        parsed = ReviewResult.model_validate(JsonOutputParser().parse(response.text))
        result = {"aspect": state["aspect"], **parsed.model_dump()}
    except ValueError:
        # 解析失败不能伪装成正常评分。
        result = {"aspect": state["aspect"], "issues": ["审查结果解析失败"], "score": None}
    return {"review_results": [result]}


async def generate_report(state: ReviewState):
    scores = [item["score"] for item in state["review_results"] if item["score"] is not None]
    score_text = f"{sum(scores) / len(scores):.1f}/10" if scores else "无法评分"
    details = "\n\n".join(
        f"【{item['aspect']}】评分：{item['score']}\n问题：{item['issues']}"
        for item in state["review_results"]
    )
    response = await llm.ainvoke([HumanMessage(content=
        f"根据以下代码审查结果汇总主要问题和改进建议，明确标记解析失败的维度：\n{details}"
    )])
    return {"report": f"综合评分（有效维度）：{score_text}\n\n{response.text}"}


def build_graph():
    graph = StateGraph(ReviewState)
    graph.add_node("review_agent", review_agent)
    graph.add_node("generate_report", generate_report)
    graph.add_conditional_edges(START, dispatch_reviews, ["review_agent"])
    graph.add_edge("review_agent", "generate_report")
    graph.add_edge("generate_report", END)
    return graph.compile()


graph = build_graph()


async def review(code: str, language: str = "TypeScript"):
    start_time = perf_counter()
    result = await graph.ainvoke({"code": code, "language": language})
    return {"language": language, "review_results": result["review_results"], "report": result["report"],
            "total_time": f"{(perf_counter() - start_time) * 1000:.0f}ms"}
