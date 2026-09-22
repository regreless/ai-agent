"""分类后通过条件边进入对应处理节点。"""

from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.config import llm

HANDLERS = {
    "technical": "你是技术专家，专门回答技术相关问题。",
    "pricing": "你是商务专员，回答费用问题；未知具体价格时请用户联系商务，不要编造价格。",
    "general": "你是客服专家，友好回答用户的问题。",
}


class RoutingState(TypedDict):
    user_input: str
    category: str
    response: str


async def classify(state: RoutingState):
    response = await llm.ainvoke(
        [
            HumanMessage(
                content="把用户问题分类，只输出 technical（技术）、pricing（费用）或 general（其他）：\n"
                + state["user_input"]
            )
        ]
    )
    category = response.text.strip().lower()
    return {"category": category if category in HANDLERS else "general"}


def make_handler(system_prompt: str):
    async def handle_question(state: RoutingState):
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=state["user_input"]),
            ]
        )
        return {"response": response.text}

    return handle_question


def build_graph():
    graph = StateGraph(RoutingState)
    graph.add_node("classify", classify)
    graph.add_edge(START, "classify")
    for category, prompt in HANDLERS.items():
        graph.add_node(category, make_handler(prompt))
        graph.add_edge(category, END)
    graph.add_conditional_edges(
        "classify",
        lambda state: state["category"],
        {category: category for category in HANDLERS},
    )
    return graph.compile()


graph = build_graph()


async def route_chat(user_input: str):
    result = await graph.ainvoke({"user_input": user_input})
    return {
        "input": user_input,
        "category": result["category"],
        "response": result["response"],
    }
