import os

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

import config.index as config


model = ChatOpenAI(
    model=config.model,
    api_key=os.environ.get(config.api_key),
    base_url=config.base_url,
    extra_body={"thinking": {"type": "disabled"}},
)

def chat_node(state: MessagesState):
    """调用模型，并把模型回复加入消息历史。"""
    messages = [
        SystemMessage(content="根据当前的历史会话，回答问题"),
        *state["messages"],
    ]
    reply = model.invoke(messages)
    return {"messages": [reply]}


# 1. 创建只有一个模型节点的对话图。
graph = StateGraph(MessagesState)
graph.add_node("chat", chat_node)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)

# 2. 加上内存存储，同一个 thread_id 会自动读取之前的消息。
app = graph.compile(checkpointer=InMemorySaver())


def chat(input_text: str, session_id: str) -> str:
    """发送消息；session_id 相同就会接着之前的对话。"""
    result = app.invoke(
        {"messages": [("user", input_text)]},
        {"configurable": {"thread_id": session_id}},
    )
    return result["messages"][-1].content


if __name__ == "__main__":
    session_id = "user_007"
    print("第1次", chat("小明有一只猫", session_id))
    print("第2次", chat("小明有两只狗", session_id))
    print("第3次", chat("小明一共有几个宠物", session_id))
