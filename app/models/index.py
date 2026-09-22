from fastapi import APIRouter
from fastapi.responses import FileResponse, StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from pydantic import BaseModel, Field
from app.config import llm

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(pattern=r"\S", description="用户输入的消息，不能为空")


class ChatSystemRequest(ChatRequest):
    system: str = Field(pattern=r"\S", description="模型的角色和行为设定")


@router.post(
    "/chat", summary="普通对话",
    description="HumanMessage 传入用户消息，ainvoke 异步调用模型，获取回复内容和 token 用量。",
)
async def base_chat(chat_request: ChatRequest):
    response = await llm.ainvoke([HumanMessage(content=chat_request.message)])
    return {
        "question": chat_request.message,
        "answer": response.content,
        "usage": response.usage_metadata,
    }


@router.post(
    "/chat-system", summary="系统对话",
    description="SystemMessage 设定角色和行为，HumanMessage 提供问题，引导模型回答。",
)
async def chat_system(chat_request: ChatSystemRequest):
    response = await llm.ainvoke([
        SystemMessage(content=chat_request.system),
        HumanMessage(content=chat_request.message),
    ])
    return {
        "system": chat_request.system,
        "question": chat_request.message,
        "answer": response.content,
        "usage": response.usage_metadata,
    }


@router.post(
    "/chat-parser", summary="解析器对话",
    description="通过 | 串联模型和 StrOutputParser，将模型回复解析为字符串。",
)
async def chat_parser(chat_request: ChatRequest):
    chain = llm | StrOutputParser()  # 模型输出 → 字符串
    answer = await chain.ainvoke([HumanMessage(content=chat_request.message)])
    return {"question": chat_request.message, "answer": answer}


@router.post(
    "/chat-stream", summary="流式对话",
    description="astream 逐段生成文字，async for 与 yield 配合 StreamingResponse，通过 SSE 推送。",
)
async def chat_stream(chat_request: ChatRequest):
    chain = llm | StrOutputParser()

    async def event_stream():
        async for text in chain.astream([HumanMessage(content=chat_request.message)]):
            if text:
                content = text.replace("\r\n", "\n").replace("\r", "\n")
                yield "data: " + content.replace("\n", "\ndata: ") + "\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no",
        },
    )
