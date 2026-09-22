"""起草 → interrupt 人工审批 → 修改、模拟发送或取消。"""

import asyncio
from typing import TypedDict
from weakref import WeakValueDictionary

from fastapi import HTTPException
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

from app.config import llm


class EmailDraft(BaseModel):
    subject: str = Field(pattern=r"\S")
    recipient: str = Field(pattern=r"\S")
    body: str = Field(pattern=r"\S")


class EmailState(TypedDict):
    email_request: str
    draft_email: dict[str, str]
    approval_status: str
    modify_feedback: str
    revision_count: int
    final_status: str


async def draft_node(state: EmailState):
    feedback = state.get("modify_feedback", "")
    prompt = f"根据请求起草邮件：{state['email_request']}"
    if feedback:
        prompt += f"\n修改意见：{feedback}\n上次草稿：{state['draft_email']}"
    prompt += '\n只输出 JSON：{"subject":"主题","recipient":"收件人","body":"正文"}'
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    try:
        draft = EmailDraft.model_validate(
            JsonOutputParser().parse(response.text)
        ).model_dump()
    except ValueError:
        draft = {"subject": "草稿", "recipient": "未知", "body": response.text}
    return {
        "draft_email": draft,
        "approval_status": "pending",
        "modify_feedback": "",
        "revision_count": state.get("revision_count", 0) + int(bool(feedback)),
        "final_status": "",
    }


def wait_node(state: EmailState):
    decision = interrupt(
        {
            "type": "email_review",
            "draft": state["draft_email"],
            "revision_count": state["revision_count"],
            "options": {
                "approve": "批准（模拟发送）",
                "reject": "驳回",
                "modify": "修改",
            },
        }
    )
    if decision["action"] == "modify":
        return {
            "approval_status": "need_modify",
            "modify_feedback": decision["feedback"],
        }
    return {
        "approval_status": "approved" if decision["action"] == "approve" else "rejected"
    }


def finish_node(state: EmailState):
    final_status = "邮件已取消，未发送"
    if state["approval_status"] == "approved":
        final_status = (
            f"模拟发送完成：收件人 {state['draft_email']['recipient']}，未发送真实邮件"
        )
    return {"final_status": final_status}


def build_graph():
    graph = StateGraph(EmailState)
    for node in (draft_node, wait_node, finish_node):
        graph.add_node(node.__name__, node)
    graph.add_edge(START, "draft_node")
    graph.add_edge("draft_node", "wait_node")
    graph.add_conditional_edges(
        "wait_node",
        lambda state: state["approval_status"],
        {
            "approved": "finish_node",
            "need_modify": "draft_node",
            "rejected": "finish_node",
        },
    )
    graph.add_edge("finish_node", END)
    return graph.compile(checkpointer=InMemorySaver())


graph = build_graph()
thread_locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()


def get_thread_lock(thread_id: str):
    # 同一审批线程串行修改，避免重复批准或起草覆盖。
    return thread_locks.setdefault(thread_id, asyncio.Lock())


def format_result(thread_id: str, result: dict):
    interruptions = result.get("__interrupt__", ())
    return {
        "thread_id": thread_id,
        "status": "waiting_for_approval" if interruptions else "completed",
        "review_data": interruptions[0].value if interruptions else None,
        "current_state": {
            key: value for key, value in result.items() if key != "__interrupt__"
        },
    }


async def start(request: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    async with get_thread_lock(thread_id):
        state = await graph.aget_state(config)
        if state.values:
            raise HTTPException(
                status_code=409, detail="thread_id 已存在，请使用新线程或继续审批"
            )
        result = await graph.ainvoke(
            {"email_request": request, "revision_count": 0}, config
        )
    return format_result(thread_id, result)


async def resume(thread_id: str, action: str, feedback: str = ""):
    if action not in {"approve", "reject", "modify"} or (
        action == "modify" and not feedback.strip()
    ):
        raise HTTPException(status_code=422, detail="无效审批操作或修改意见为空")
    config = {"configurable": {"thread_id": thread_id}}
    async with get_thread_lock(thread_id):
        state = await graph.aget_state(config)
        if not state.values:
            raise HTTPException(status_code=404, detail="审批线程不存在")
        if not any(task.interrupts for task in state.tasks):
            raise HTTPException(status_code=409, detail="当前线程没有等待审批的邮件")
        result = await graph.ainvoke(
            Command(resume={"action": action, "feedback": feedback}), config
        )
    return format_result(thread_id, result)


async def get_status(thread_id: str):
    state = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    if not state.values:
        raise HTTPException(status_code=404, detail="审批线程不存在")
    interruptions = tuple(item for task in state.tasks for item in task.interrupts)
    return format_result(thread_id, {**state.values, "__interrupt__": interruptions})
