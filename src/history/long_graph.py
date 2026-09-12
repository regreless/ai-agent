import atexit
import os
import sqlite3
from typing import Annotated

from typing_extensions import TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from src.config import index as config

model = ChatOpenAI(
    model=config.model,
    api_key=os.environ.get(config.api_key),
    base_url=config.base_url,
    extra_body={"thinking": {"type": "disabled"}},
)


class ChatState(TypedDict):
    # 新 API：用 reducer 声明 messages 字段，节点返回的新消息会自动追加到历史。
    messages: Annotated[list[AnyMessage], add_messages]


SYSTEM_MESSAGE = SystemMessage(content="根据当前的历史会话，回答问题")


def chat_node(state: ChatState) -> dict[str, list[AnyMessage]]:
    """调用模型，并将回复作为状态增量交给 LangGraph 保存。"""
    reply = model.invoke([SYSTEM_MESSAGE, *state["messages"]])
    return {"messages": [reply]}


# 新 API：使用 StateGraph 构建对话流程，不再使用 RunnableWithMessageHistory。
builder = StateGraph()
builder.add_node("chat", chat_node)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

# 新 API：checkpointer 负责持久化整个图状态；SQLite 可在程序重启后恢复历史。
CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "chat_history")
CHECKPOINT_PATH = os.path.join(CHECKPOINT_DIR, "checkpoints.sqlite")
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

checkpoint_connection = sqlite3.connect(CHECKPOINT_PATH, check_same_thread=False)
checkpointer = SqliteSaver(checkpoint_connection)
app = builder.compile(checkpointer=checkpointer)
atexit.register(checkpoint_connection.close)


def chat(input_text: str, session_id: str) -> str:
    """发送一条消息；相同 session_id 会延续同一个会话。"""
    # 新 API 使用 thread_id 标识持久化会话。
    run_config = {"configurable": {"thread_id": session_id}}
    result = app.invoke(
        {"messages": [HumanMessage(content=input_text)]},
        config=run_config,
    )
    return result["messages"][-1].text


if __name__ == "__main__":
    session_id = "user_007"
    print("第1次", chat("小明有一只猫", session_id))
    print("第2次", chat("小明有两只狗", session_id))
    print("第3次", chat("小明一共有几个宠物", session_id))
