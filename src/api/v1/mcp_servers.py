from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from src.api.deps import get_current_user
from src.db.session import get_db
from src.models.entities import MCPServer, User
from src.schemas.common import ApiResponse

router = APIRouter()


class MCPCreate(BaseModel):
    name: str
    description: str = ""
    command: str = "python"
    args: list[str] = []
    tools: list[str] = []


@router.get("", response_model=ApiResponse[list[dict]])
async def list_mcp(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
):
    rows = (
        (await db.execute(select(MCPServer).where(MCPServer.tenant_id == user.tenant_id)))
    ).scalars().all()

    return ApiResponse(
        data=[
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "command": m.command,
                "args": m.args,
                "tools": m.tools,
            }
            for m in rows
        ]
    )


@router.post("", response_model=ApiResponse[dict])
async def create_mcp(
        req: MCPCreate,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    m = MCPServer(tenant_id=user.tenant_id, **req.model_dump())
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return ApiResponse(data={"id": m.id, "name": m.name})
