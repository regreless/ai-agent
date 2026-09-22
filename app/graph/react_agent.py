"""带会话历史的工具对话：模型决定调用工具或结束，计算器仅允许基本算术。"""

import operator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import llm

OPERATORS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
}
MOCK_WEATHER = {
    "北京": "晴，25°C，东北风 3 级",
    "上海": "多云，28°C，东风 2 级",
    "武汉": "晴，30°C，南风 1 级",
    "广州": "雷阵雨，32°C，南风 2 级",
}


@tool
def calculator(a: float, b: float, operation: str) -> str:
    """对两个数进行运算，operation 支持 +、-、*、/；组合计算需分步调用。"""
    calculate = OPERATORS.get(operation)
    if calculate is None:
        return "计算错误：不支持的运算符，请使用 +、-、*、/"
    try:
        return f"计算结果：{a} {operation} {b} = {calculate(a, b)}"
    except ZeroDivisionError:
        return "计算错误：除数不能为零"


@tool
def get_weather(city: str) -> str:
    """返回城市的模拟天气数据，仅供工具调用演示，不代表实时天气。"""
    return f"模拟天气：{city}：{MOCK_WEATHER.get(city, '暂无模拟数据')}"


tool_list = [calculator, get_weather]


async def call_model(state: MessagesState):
    response = await llm.bind_tools(tool_list).ainvoke(
        [
            SystemMessage(
                content="你是专业助手，可使用 calculator 计算和 get_weather 查询模拟天气。明确说明天气是模拟数据。"
            ),
            *state["messages"],
        ]
    )
    return {"messages": [response]}


graph_builder = StateGraph(MessagesState)
graph_builder.add_node("call_model", call_model)
graph_builder.add_node("tools", ToolNode(tool_list, handle_tool_errors=True))
graph_builder.add_edge(START, "call_model")
graph_builder.add_conditional_edges("call_model", tools_condition)
graph_builder.add_edge("tools", "call_model")
graph = graph_builder.compile(checkpointer=InMemorySaver())


async def chat(thread_id: str, message: str):
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        {"configurable": {"thread_id": thread_id}, "recursion_limit": 10},
    )
    return {"answer": result["messages"][-1].text}
