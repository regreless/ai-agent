from uuid import uuid4

import streamlit as st

from rag import RagService

st.title("聊天小助手")
st.divider()

# 1. URL 保存会话 ID，刷新后继续使用同一份历史。
if not st.query_params.get("session_id"):
    st.query_params["session_id"] = str(uuid4())

rag = RagService(session_id=st.query_params["session_id"])

# 2. 显示历史，页面只处理 user 和 ai 两种角色。
history = rag.get_history() or [{"role": "ai", "content": "有什么可以帮助你"}]
for msg in history:
    st.chat_message(msg["role"]).write(msg["content"])

# 3. 接收问题并流式显示回答，历史由 RAG 自动保存。
prompt = st.chat_input()
if prompt:
    st.chat_message("user").write(prompt)
    with st.chat_message("ai"):
        st.write_stream(rag.stream(input=prompt))
