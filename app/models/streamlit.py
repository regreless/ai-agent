from time import perf_counter

import httpx
import streamlit as st


def show_message(chat_message):
    with st.chat_message(chat_message["role"]):
        if "error" in chat_message:
            st.error(chat_message["error"])
        else:
            st.markdown(chat_message["content"])
        if "response" in chat_message:
            st.caption(f"耗时：{chat_message['elapsed']:.2f} 秒")
            st.write("Token 用量", chat_message["response"].get("usage"))
            with st.expander("原始响应"):
                st.json(chat_message["response"])


st.set_page_config(page_title="模型调试", page_icon="💬")
st.title("模型调试")
st.caption("每次只发送当前消息，历史记录仅用于展示。")
st.session_state.setdefault("chat_history", [])

with st.sidebar:
    api_url = st.text_input("接口地址", "http://127.0.0.1:8000/models/chat")
    timeout_seconds = st.number_input("超时（秒）", 1, 600, 120)
    if st.button("清空记录"):
        st.session_state.chat_history = []

for chat_message in st.session_state.chat_history:
    show_message(chat_message)

if message := st.chat_input("输入消息"):
    if not message.strip():
        st.warning("消息不能为空")
        st.stop()

    chat_message = {"role": "user", "content": message}
    st.session_state.chat_history.append(chat_message)
    show_message(chat_message)
    chat_message = {"role": "assistant"}
    start_time = perf_counter()

    try:
        with st.spinner("正在回答…"):
            response = httpx.post(
                api_url.strip(), json={"message": message}, timeout=timeout_seconds
            )
            response.raise_for_status()
            response_data = response.json()
            if not isinstance(response_data, dict) or not isinstance(response_data.get("answer"), str):
                raise ValueError("响应中缺少字符串类型的 answer")
            chat_message.update(
                content=response_data["answer"],
                response=response_data,
                elapsed=perf_counter() - start_time,
            )
    except httpx.HTTPStatusError as error:
        chat_message["error"] = f"HTTP {error.response.status_code}：{error.response.text}"
    except (httpx.RequestError, ValueError) as error:
        chat_message["error"] = f"请求失败，请检查服务、地址和超时设置：{error}"

    st.session_state.chat_history.append(chat_message)
    show_message(chat_message)
