import json, uuid, hashlib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.chat import Conversation, Message
from src.schemas.chat import *
from src.llm.schemas import *
from src.llm.provider import BaseLLMProvider
from src.tools.ecommerce import tool_schema, execute_tool
from src.utils.cache import cache


def latest_user(req):
    return next(
        (m.content for m in reversed(req.messages) if m.role == MessageRole.user),
        req.messages[-1].content,
    )


def to_llm_messages(req):
    return [
        LLMMessage(role=LLMRole(m.role.value), content=m.content) for m in req.messages
    ]


async def save_messages(db, sid, user, assistant, model, usage):
    db.add(
        Message(
            id="m_" + uuid.uuid4().hex[:8],
            conversation_id=sid,
            role="user",
            content=user,
            model=model,
            prompt_tokens=usage.prompt_tokens,
        )
    )
    db.add(
        Message(
            id="m_" + uuid.uuid4().hex[:8],
            conversation_id=sid,
            role="assistant",
            content=assistant,
            model=model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )
    )
    await db.commit()


async def chat_with_ai(
    req: ChatRequest, db: AsyncSession, llm: BaseLLMProvider
) -> ChatResponse:
    user = latest_user(req)
    model = req.model
    key = "chat:" + hashlib.sha256(user.encode()).hexdigest()
    if req.prompt_scenario != "ecommerce_customer_service":
        cached = await cache.get(key)
        if cached:
            return ChatResponse(
                answer=cached,
                model=model,
                session_id=req.session_id,
                metadata={"cache_hit": True},
            )
    if req.prompt_scenario == "ecommerce_customer_service":
        first = await llm.chat(
            LLMRequest(
                model=model,
                messages=[
                    LLMMessage(
                        role=LLMRole.system,
                        content="你是电商客服，订单物流问题要调用工具。",
                    ),
                    LLMMessage(role=LLMRole.user, content=user),
                ],
                tools=[tool_schema()],
                tool_choice="auto",
            )
        )
        tool_results = []
        if first.tool_calls:
            msgs = [
                LLMMessage(
                    role=LLMRole.system, content="根据工具结果生成友好客服回复。"
                ),
                LLMMessage(role=LLMRole.user, content=user),
                LLMMessage(role=LLMRole.assistant, tool_calls=first.tool_calls),
            ]
            for tc in first.tool_calls:
                result = await execute_tool(tc.name, tc.arguments)
                content = json.dumps(
                    {"success": True, "data": result.model_dump()}, ensure_ascii=False
                )
                tool_results.append(
                    {
                        "tool_name": tc.name,
                        "arguments": tc.arguments,
                        "result": result.model_dump(),
                    }
                )
                msgs.append(
                    LLMMessage(role=LLMRole.tool, tool_call_id=tc.id, content=content)
                )
            final = await llm.chat(
                LLMRequest(model=model, messages=msgs, temperature=0.3)
            )
            ans = final.content
            usage = final.usage
            if req.session_id:
                await save_messages(db, req.session_id, user, ans, model, usage)
            return ChatResponse(
                answer=ans,
                model=model,
                session_id=req.session_id,
                usage=TokenUsage(**usage.model_dump()),
                metadata={
                    "tool_calls": [t.model_dump() for t in first.tool_calls],
                    "tool_results": tool_results,
                },
            )
    r = await llm.chat(
        LLMRequest(
            model=model, messages=to_llm_messages(req), temperature=req.temperature
        )
    )
    await cache.set(key, r.content)
    if req.session_id:
        await save_messages(db, req.session_id, user, r.content, model, r.usage)
    return ChatResponse(
        answer=r.content,
        model=model,
        session_id=req.session_id,
        usage=TokenUsage(**r.usage.model_dump()),
        metadata={"cache_hit": False},
    )


async def list_messages(db, sid):
    res = await db.execute(
        select(Message)
        .where(Message.conversation_id == sid)
        .order_by(Message.created_at.asc())
    )
    return [
        ChatMessage(role=MessageRole(m.role), content=m.content)
        for m in res.scalars().all()
    ]
