"""通过 FastAPI 测试邮件起草和人工审批。"""

from urllib.parse import quote, urlsplit
from uuid import uuid4

import httpx
import streamlit as st


def request_api(method: str, path: str, payload: dict | None = None):
    try:
        with st.spinner("正在处理…"):
            response = httpx.request(
                method, f"{api_base_url}/graph/email/{path}",
                json=payload, timeout=120,
                trust_env=urlsplit(api_base_url).hostname not in {"localhost", "127.0.0.1", "::1"},
            )
            response.raise_for_status()
            st.session_state.email_result = response.json()
    except httpx.HTTPStatusError as error:
        try:
            detail = error.response.json().get("detail", error.response.text)
        except ValueError:
            detail = error.response.text
        detail = detail or error.response.reason_phrase or "服务未返回错误详情"
        st.error(f"请求失败（{error.response.status_code}）：{detail}")
    except httpx.RequestError as error:
        st.error(f"无法完成请求：{error}。请检查后端地址，超时后可查询状态。")
    else:
        st.rerun()


st.set_page_config(page_title="邮件审批测试", page_icon="✉️")
st.title("邮件审批测试")
st.caption("批准仅模拟发送，不会发送真实邮件。后端重启后，内存中的审批记录会丢失。")
st.session_state.setdefault("thread_id", str(uuid4()))

with st.sidebar:
    api_base_url = st.text_input("后端地址", "http://127.0.0.1:8000").strip().rstrip("/")
    if st.button("新建审批"):
        st.session_state.thread_id = str(uuid4())
    thread_id = st.text_input("审批线程 ID", key="thread_id").strip()
    valid_context = bool(api_base_url and thread_id)
    query_status = st.button("查询 / 刷新状态", disabled=not valid_context)

context = (api_base_url, thread_id)
if st.session_state.get("email_context") != context:
    st.session_state.email_context = context
    st.session_state.email_result = None

thread_path = quote(thread_id, safe="")
if query_status:
    request_api("GET", f"{thread_path}/status")

result = st.session_state.email_result
with st.form("draft_form"):
    email_request = st.text_area("邮件需求", placeholder="给 demo@example.com 写一封会议邀请，时间为明天下午三点。")
    start_clicked = st.form_submit_button("起草邮件", disabled=not valid_context or result is not None)
if start_clicked:
    if email_request.strip():
        request_api("POST", "start", {"thread_id": thread_id, "request": email_request})
    else:
        st.warning("请填写邮件需求。")

if result:
    current_state = result["current_state"]
    waiting = result["status"] == "waiting_for_approval"
    st.subheader("待审批" if waiting else "已结束")
    st.caption(f"修改次数：{current_state.get('revision_count', 0)}")
    draft_email = current_state.get("draft_email", {})
    st.text(f"收件人：{draft_email.get('recipient', '')}")
    st.text(f"主题：{draft_email.get('subject', '')}")
    st.text(draft_email.get("body", ""))

    if waiting:
        approve_column, reject_column = st.columns(2)
        if approve_column.button("批准（模拟发送）", use_container_width=True):
            request_api("POST", f"{thread_path}/approve")
        if reject_column.button("驳回", use_container_width=True):
            request_api("POST", f"{thread_path}/reject")
        with st.form("modify_form", clear_on_submit=True):
            feedback = st.text_area("修改意见")
            modify_clicked = st.form_submit_button("修改并重新起草")
        if modify_clicked:
            if feedback.strip():
                request_api("POST", f"{thread_path}/modify", {"feedback": feedback})
            else:
                st.warning("请填写修改意见。")
    else:
        st.success(current_state.get("final_status", "审批已结束"))

    with st.expander("接口返回数据"):
        st.json(result)
