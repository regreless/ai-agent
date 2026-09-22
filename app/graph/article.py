"""文章 → 关键词 → 摘要，节点只返回需要更新的状态。"""

import operator
import re
from time import perf_counter
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from app.config import llm


class ArticleState(TypedDict):
    article: str
    keywords: Annotated[list[str], operator.add]
    summary: str
    log: Annotated[list[str], operator.add]


async def extract_keywords(state: ArticleState):
    start_time = perf_counter()
    response = await llm.ainvoke(
        [
            HumanMessage(
                content=f"从以下文章提取 5-8 个核心关键词，只输出关键词，逗号分隔：\n\n{state['article']}"
            )
        ]
    )
    return {
        "keywords": [
            word.strip() for word in re.split(r"[,，]", response.text) if word.strip()
        ],
        "log": [f"关键词提取完成（{(perf_counter() - start_time) * 1000:.0f}ms）"],
    }


async def generate_summary(state: ArticleState):
    start_time = perf_counter()
    response = await llm.ainvoke(
        [
            HumanMessage(
                content=f"生成 200 字以内的摘要。关键词参考：{'、'.join(state['keywords'])}\n文章：{state['article']}"
            )
        ]
    )
    return {
        "summary": response.text,
        "log": [f"摘要生成完成（{(perf_counter() - start_time) * 1000:.0f}ms）"],
    }


def build_graph():
    graph = StateGraph(ArticleState)
    graph.add_node("extract_keywords", extract_keywords)
    graph.add_node("generate_summary", generate_summary)
    graph.add_edge(START, "extract_keywords")
    graph.add_edge("extract_keywords", "generate_summary")
    graph.add_edge("generate_summary", END)
    return graph.compile()


graph = build_graph()
print(graph.get_graph().draw_mermaid())


async def process(article: str):
    result = await graph.ainvoke({"article": article})
    return {key: result[key] for key in ("keywords", "summary", "log")}
