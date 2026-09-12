from contextlib import contextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, MessagesState, StateGraph

DB_PATH = Path(__file__).parent / "chat_history" / "checkpoints.sqlite"


def get_history(session_id: str, db_path=DB_PATH):
    """读取该会话最新快照中的消息，不执行模型。"""
    if not Path(db_path).exists():
        return []
    with SqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        snapshot = checkpointer.get_tuple({"configurable": {"thread_id": session_id}})
        return snapshot.checkpoint["channel_values"].get("messages", []) if snapshot else []


@contextmanager
def create_chat(reply, db_path=DB_PATH, *, stream=False):
    """chat 返回完整文本；stream=True 时返回文本迭代器，需在 with 内消费完。"""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    def respond(state: MessagesState):
        # messages 已包含历史和本轮问题，只返回新回答，由 MessagesState 追加。
        return {"messages": [reply(state["messages"])]}

    graph = StateGraph(MessagesState)
    graph.add_node("chat", respond)
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)

    with SqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        app = graph.compile(checkpointer=checkpointer)

        def chat(input_text: str, session_id: str):
            inputs = {"messages": [("user", input_text)]}
            config = {"configurable": {"thread_id": session_id}}
            if stream:
                return (
                    message.text
                    for message, metadata in app.stream(inputs, config, stream_mode="messages")
                    if metadata.get("langgraph_node") == "chat" and message.text
                )
            return app.invoke(inputs, config)["messages"][-1].text

        yield chat
