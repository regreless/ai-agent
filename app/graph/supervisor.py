"""协调者按需选择工作节点，每个工作节点最多执行一次。"""

import operator
from typing import Annotated

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from app.config import llm

WORKERS = {
    "researcher": "你是研究员，整理信息并提供调研结果，不要声称进行过实际联网搜索。",
    "analyst": "你是分析师，擅长数据分析和逻辑推理。",
    "writer": "你是作家，擅长撰写报告和优化表达。",
}


class SupervisorState(MessagesState):
    next_agent: str
    completed_agents: Annotated[list[str], operator.add]


async def supervise(state: SupervisorState):
    completed_agents = state.get("completed_agents", [])
    available_agents = [name for name in WORKERS if name not in completed_agents]
    if not available_agents:
        return {"next_agent": "FINISH"}
    response = await llm.ainvoke(
        [
            SystemMessage(
                content="你是任务协调者。researcher 整理信息，analyst 分析推理，writer 撰写报告。"
                f"已完成：{completed_agents}。只输出下一个节点名称或 FINISH。"
                f"可选：{', '.join(available_agents)}，FINISH。"
            ),
            *state["messages"],
        ]
    )
    next_agent = response.text.strip()
    if next_agent not in available_agents:
        next_agent = "FINISH"
    return {
        "next_agent": next_agent,
        "messages": [AIMessage(content=f"[supervisor] 下一步：{next_agent}")],
    }


def create_worker(name: str, system_prompt: str):
    async def work(state: SupervisorState):
        user_message = next(
            message for message in state["messages"] if message.type == "human"
        )
        context = "\n".join(message.text for message in state["messages"][-4:])
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=f"原始任务：{user_message.text}\n当前上下文：\n{context}"
                ),
            ]
        )
        return {
            "messages": [AIMessage(content=response.text, name=name)],
            "completed_agents": [name],
        }

    return work


def build_graph():
    graph = StateGraph(SupervisorState)
    graph.add_node("supervisor", supervise)
    graph.add_edge(START, "supervisor")
    for name, prompt in WORKERS.items():
        graph.add_node(name, create_worker(name, prompt))
        graph.add_edge(name, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda state: state["next_agent"],
        {**{name: name for name in WORKERS}, "FINISH": END},
    )
    return graph.compile()


graph = build_graph()


async def run(user_input: str):
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=user_input)]}, {"recursion_limit": 12}
    )
    worker_messages = [
        message for message in result["messages"] if message.name in WORKERS
    ]
    writer_messages = [
        message for message in worker_messages if message.name == "writer"
    ]
    final_messages = writer_messages or worker_messages
    return {
        "final_response": final_messages[-1].text if final_messages else "没有生成结果",
        "agent_log": "\n".join(
            f"[{message.name}] {message.text}" if message.name else message.text
            for message in result["messages"]
            if message.type == "ai"
        ),
        "completed_agents": result.get("completed_agents", []),
    }
