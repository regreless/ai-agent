"""收集素材 → 制定大纲 → 撰写初稿 → 编辑定稿。"""

import operator
from time import perf_counter
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from app.config import llm


class PipelineState(TypedDict):
    topic: str
    research: str
    outline: str
    draft: str
    final_article: str
    process: Annotated[list[str], operator.add]


async def research_agent(state: PipelineState):
    response = await llm.ainvoke(
        [
            HumanMessage(
                content=f"你是研究员，为 {state['topic']} 整理背景、3-5 个核心要点和典型案例。每条不超过 50 字。"
            )
        ]
    )
    return {"research": response.text, "process": ["素材收集完成"]}


async def outline_agent(state: PipelineState):
    response = await llm.ainvoke(
        [
            HumanMessage(
                content=f"为 {state['topic']} 制定 3-5 条写作大纲，每条不超过 20 字。素材：\n{state['research']}"
            )
        ]
    )
    return {"outline": response.text, "process": ["大纲制定完成"]}


async def writer_agent(state: PipelineState):
    response = await llm.ainvoke(
        [
            HumanMessage(
                content=f"写一篇 300-500 字文章。主题：{state['topic']}\n大纲：{state['outline']}\n素材：{state['research']}"
            )
        ]
    )
    return {"draft": response.text, "process": ["初稿撰写完成"]}


async def review_agent(state: PipelineState):
    response = await llm.ainvoke(
        [
            HumanMessage(
                content=f"你是编辑，优化以下文章，直接输出优化后全文：\n{state['draft']}"
            )
        ]
    )
    return {"final_article": response.text, "process": ["最终定稿完成"]}


def build_graph():
    graph = StateGraph(PipelineState)
    previous_node = START
    for node in (research_agent, outline_agent, writer_agent, review_agent):
        graph.add_node(node.__name__, node)
        graph.add_edge(previous_node, node.__name__)
        previous_node = node.__name__
    graph.add_edge(previous_node, END)
    return graph.compile()


graph = build_graph()


async def process(topic: str):
    start_time = perf_counter()
    result = await graph.ainvoke({"topic": topic})
    return {
        "topic": topic,
        "progress": result["process"],
        "article": result["final_article"],
        "total_time": f"{perf_counter() - start_time:.3f} seconds",
    }
