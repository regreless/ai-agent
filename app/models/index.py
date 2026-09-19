from fastapi import FastAPI
from langchain_core.messages import HumanMessage

from pydantic import BaseModel, Field
from app.config import llm

app = FastAPI()


class ChatRequest(BaseModel):
    message: str = Field(pattern=r"\S", description="用户输入的消息，不能为空")


@app.post("/models/chat")
async def base_chat(chat_request: ChatRequest):
    response = await llm.ainvoke([HumanMessage(content=chat_request.message)])
    return {
        "question": chat_request.message,
        "answer": response.content,
        "usage": response.usage_metadata,
    }
