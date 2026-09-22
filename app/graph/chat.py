"""按 thread_id 保存对话历史；历史仅存于内存，服务重启后清空。"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from app.config import llm


async def call_model(state: MessagesState):
    response = await llm.ainvoke([
        SystemMessage(content="你是专业的 AI 助手，请结合对话上下文简洁回答。"),
        *state["messages"],
    ])
    return {"messages": [response]}


graph = StateGraph(MessagesState)
graph.add_node("call_model", call_model)
graph.add_edge(START, "call_model")
graph.add_edge("call_model", END)
memory_graph = graph.compile(checkpointer=InMemorySaver())


async def memory_chat(thread_id: str, message: str):
    result = await memory_graph.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        {"configurable": {"thread_id": thread_id}},
    )
    return {"answer": result["messages"][-1].text}


async def get_history(thread_id: str):
    state = await memory_graph.aget_state({"configurable": {"thread_id": thread_id}})
    return [
        {
            "index": index,
            "role": "user" if message.type == "human" else "assistant",
            "content": message.content,
        }
        for index, message in enumerate(state.values.get("messages", []))
    ]
