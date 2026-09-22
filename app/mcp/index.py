"""HTTP 入口：接收消息，运行 MCP Agent。"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.mcp import agent

router = APIRouter()


class AgentRequest(BaseModel):
    message: str = Field(pattern=r"\S")


@router.post("/agent/run", summary="运行 MCP Agent（最多 6 轮）")
async def run_agent(agent_request: AgentRequest):
    return await agent.run_agent(agent_request.message)
