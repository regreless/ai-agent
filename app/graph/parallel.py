"""Send 动态分发独立子任务，reducer 合并后生成报告。"""

import operator
from time import perf_counter
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.config import llm


class ParallelState(TypedDict):
    task: str
    sub_tasks: list[str]
    results: Annotated[list[dict[str, str]], operator.add]
    final_report: str


class SubState(TypedDict):
    task: str


async def split_task(state: ParallelState):
    response = await llm.ainvoke([HumanMessage(content=
        f"把以下任务拆成 3 个独立子任务，每行一个，不要编号：\n{state['task']}"
    )])
    sub_tasks = [line.strip() for line in response.text.splitlines() if line.strip()][:3]
    # 空输出也必须进入处理和汇总节点，避免静默结束。
    return {"sub_tasks": sub_tasks or [state["task"]]}


def dispatch_tasks(state: ParallelState):
    return [Send("process_sub_task", {"task": task}) for task in state["sub_tasks"]]


async def process_sub_task(state: SubState):
    response = await llm.ainvoke([HumanMessage(content=f"请完成以下任务，100 字以内：\n{state['task']}")])
    return {"results": [{"task": state["task"], "result": response.text}]}


async def merge_results(state: ParallelState):
    details = "\n\n".join(f"子任务：{item['task']}\n结果：{item['result']}" for item in state["results"])
    response = await llm.ainvoke([HumanMessage(content=f"根据以下结果生成 200 字综合报告：\n{details}")])
    return {"final_report": response.text}


def build_graph():
    graph = StateGraph(ParallelState)
    graph.add_node("split_task", split_task)
    graph.add_node("process_sub_task", process_sub_task)
    graph.add_node("merge_results", merge_results)
    graph.add_edge(START, "split_task")
    graph.add_conditional_edges("split_task", dispatch_tasks, ["process_sub_task"])
    graph.add_edge("process_sub_task", "merge_results")
    graph.add_edge("merge_results", END)
    return graph.compile()


graph = build_graph()


async def parallel_chat(task: str):
    start_time = perf_counter()
    result = await graph.ainvoke({"task": task})
    return {"sub_tasks": result["sub_tasks"], "results": result["results"],
            "final_report": result["final_report"], "total_time": f"{(perf_counter() - start_time) * 1000:.0f}ms"}
