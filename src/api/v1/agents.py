from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.api.deps import get_current_user
from src.db.session import get_db
from src.models.entities import Agent, User
from src.schemas.common import ApiResponse

router = APIRouter()


class AgentCreate(BaseModel):
    name: str
    code: str
    description: str = ''
    system_prompt: str
    model_provider_id: str
    knowledge_base_ids: list[str] = []
    tool_ids: list[str] = []
    mcp_server_ids: list[str] = []
    mode: str = 'rag_tool_mcp'


@router.get("", response_model=ApiResponse[list[dict]])
async def list_agents(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (await db.execute(select(Agent).where(Agent.tenant_id == user.tenant_id))).scalars().all()
    return ApiResponse(
        data=[
            {
                "id": a.id,
                "name": a.name,
                "code": a.code,
                "status": a.status,
                "mode": a.mode,
                "description": a.description,
            }
            for a in rows
        ]
    )


@router.post("", response_model=ApiResponse[dict])
async def create_agent(
        req: AgentCreate,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
):
    a = Agent(tenant_id=user.tenant_id, **req.model_dump())
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return ApiResponse(data={"id": a.id, "name": a.name, "code": a.code})


@router.get("/{agent_id}", response_model=ApiResponse[dict])
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    a = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenant_id == user.tenant_id))).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return ApiResponse(
        data={
            "id": a.id,
            "name": a.name,
            "code": a.code,
            "description": a.description,
            "system_prompt": a.system_prompt,
            "knowledge_base_ids": a.knowledge_base_ids,
            "tool_ids": a.tool_ids,
            "mcp_server_ids": a.mcp_server_ids,
        }
    )
