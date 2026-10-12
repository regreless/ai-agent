import json, uuid
import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.db.session import AsyncSessionLocal
from src.models.chat import Conversation
from src.schemas.common import ApiResponse
from src.schemas.chat import (
    ChatRequest,
    ChatMessage,
    ConversationCreateRequest,
    ConversationResponse,
    ConversationListResponse,
    ConversationMessagesResponse,
)
from src.llm.provider import get_provider
from src.services.chat_service import chat_with_ai, list_messages
from src.services.structured_service import classify_intent, rag_answer, agent_plan
from src.tools.ecommerce import tool_schema

router = APIRouter()
LOGGER = logging.getLogger(__name__)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


def auth(x_api_key: str | None = Header(None)):
    if x_api_key != settings.app_api_key:
        raise HTTPException(403, "API Key 不正确")


@router.get("/health")
async def health():
    return {"status": "ok", "services": settings.app_name}


@router.post(
    "/conversations",
    response_model=ApiResponse[ConversationResponse],
    dependencies=[Depends(auth)],
)
async def create_conv(
    req: ConversationCreateRequest,
    db: AsyncSession = Depends(get_db),
    x_user_id: str | None = Header("u_demo"),
):
    conv = Conversation(
        id="c_" + uuid.uuid4().hex[:8],
        title=req.title,
        user_id=x_user_id,
        status="active",
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return ApiResponse(
        data=ConversationResponse(
            conversation_id=conv.id,
            title=conv.title,
            status=conv.status,
            created_at=str(conv.created_at),
            updated_at=str(conv.updated_at),
        )
    )


@router.get(
    "/conversations",
    response_model=ApiResponse[ConversationListResponse],
    dependencies=[Depends(auth)],
)
async def convs(
    db: AsyncSession = Depends(get_db), x_user_id: str | None = Header("u_demo")
):
    rows = (
        (
            await db.execute(
                select(Conversation).where(
                    Conversation.user_id == x_user_id, Conversation.status == "active"
                )
            )
        )
        .scalars()
        .all()
    )
    data = [
        ConversationResponse(
            conversation_id=c.id,
            title=c.title,
            status=c.status,
            created_at=str(c.created_at),
            updated_at=str(c.updated_at),
        )
        for c in rows
    ]
    return ApiResponse(data=ConversationListResponse(conversations=data))


@router.get(
    "/conversations/{cid}/messages",
    response_model=ApiResponse[ConversationMessagesResponse],
    dependencies=[Depends(auth)],
)
async def msgs(cid: str, db: AsyncSession = Depends(get_db)):
    return ApiResponse(
        data=ConversationMessagesResponse(
            conversation_id=cid, messages=await list_messages(db, cid)
        )
    )


@router.post("/chat", dependencies=[Depends(auth)])
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    x_user_id: str | None = Header("u_demo"),
):
    req.user_id = x_user_id
    return ApiResponse(data=await chat_with_ai(req, db, get_provider()))


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat/stream", dependencies=[Depends(auth)])
async def stream(
    req: ChatRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    async def gen():
        try:
            result = await chat_with_ai(req, db, get_provider())
        except Exception:
            LOGGER.exception("流式聊天处理失败")
            yield sse("error", {"message": "后端聊天处理失败，请查看 FastAPI 日志。"})
            return
        yield sse("start", {"model": result.model, "session_id": result.session_id})
        for i in range(0, len(result.answer), 8):
            yield sse("message", {"content": result.answer[i : i + 8]})
        yield sse("done", {"usage": result.usage.model_dump()})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/models")
async def models():
    return ApiResponse(
        data=[
            {"model": m, "provider": "mock" if m.startswith("mock") else "remote"}
            for m in settings.supported_model_list
        ]
    )


@router.get("/tools", dependencies=[Depends(auth)])
async def tools():
    return ApiResponse(data=[tool_schema()])


@router.post("/tools/run", dependencies=[Depends(auth)])
async def run_tool(payload: dict):
    req = ChatRequest(
        messages=[ChatMessage(role="user", content=payload.get("question", ""))],
        model=payload.get("model", "mock-chat"),
        prompt_scenario="ecommerce_customer_service",
    )
    async with AsyncSessionLocal() as db:
        return ApiResponse(
            data=(await chat_with_ai(req, db, get_provider())).model_dump()
        )


@router.post("/structured/intent", dependencies=[Depends(auth)])
async def intent(payload: dict):
    return ApiResponse(
        data=await classify_intent(
            payload.get("question", ""),
            payload.get("model", "mock-chat"),
            get_provider(),
        )
    )


@router.post("/structured/rag-answer", dependencies=[Depends(auth)])
async def rag(payload: dict):
    return ApiResponse(
        data=await rag_answer(
            payload.get("question", ""),
            payload.get("retrieved_context", ""),
            payload.get("model", "mock-chat"),
            get_provider(),
        )
    )


@router.post("/structured/agent-plan", dependencies=[Depends(auth)])
async def plan(payload: dict):
    return ApiResponse(
        data=await agent_plan(
            payload.get("goal", ""),
            payload.get("available_tools", ""),
            payload.get("constraints", "无"),
            payload.get("model", "mock-chat"),
            get_provider(),
        )
    )
