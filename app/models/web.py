import httpx
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000"
API_PATHS = {
    "普通对话": "/models/chat",
    "流式对话": "/models/chat-stream",
}


def read_stream(response):
    data_lines = []
    for line in response.iter_lines():
        if line.startswith("data:"):
            data_lines.append(line[5:].removeprefix(" "))
            continue
        if line or not data_lines:
            continue
        content = "\n".join(data_lines)
        data_lines = []
        if content == "[DONE]":
            return
        yield content


def request_chat(api_url, message):
    response = httpx.post(api_url, json={"message": message}, timeout=120)
    response.raise_for_status()
    yield response.json()["answer"]


def request_stream(api_url, message):
    with httpx.stream(
        "POST", api_url, json={"message": message}, timeout=120
    ) as response:
        response.raise_for_status()
        yield from read_stream(response)


def show_answer(api_url, message, request_handler):
    answer = ""
    answer_area = st.empty()
    with st.spinner("正在回答…"):
        try:
            for content in request_handler(api_url, message):
                answer += content
                answer_area.markdown(answer)
        except Exception as error:
            answer = f"{answer}\n\n请求失败：{error}".strip()
            answer_area.markdown(answer)
    return answer


REQUEST_HANDLERS = {
    "普通对话": request_chat,
    "流式对话": request_stream,
}


st.title("模型问答")
chat_mode = st.sidebar.radio("测试接口", list(API_PATHS))
api_url = API_BASE_URL + API_PATHS[chat_mode]
st.sidebar.caption(f"POST {api_url}")
st.session_state.setdefault("chat_history", [])

for chat_message in st.session_state.chat_history:
    with st.chat_message(chat_message["role"]):
        st.markdown(chat_message["content"])

if message := st.chat_input("输入消息"):
    st.session_state.chat_history.append({"role": "user", "content": message})
    with st.chat_message("user"):
        st.markdown(message)

    with st.chat_message("assistant"):
        answer = show_answer(api_url, message, REQUEST_HANDLERS[chat_mode])

    st.session_state.chat_history.append({"role": "assistant", "content": answer})
