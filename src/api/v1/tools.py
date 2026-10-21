from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from src.api.deps import get_current_user
from src.db.session import get_db
from src.models.entities import ToolDefinition, User
from src.schemas.common import ApiResponse

router = APIRouter()


class ToolCreate(BaseModel):
    name: str
    description: str = ""
    tool_schema: dict = Field(default_factory=dict, alias="schema")
    risk_level: str = "low"
    requires_approval: bool = False


@router.get("/", response_model=ApiResponse[list[dict]])
async def list_tools(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    rows = (
        (
            await db.execute(select(ToolDefinition).where(ToolDefinition.tenant_id == user.tenant_id))
        ).scalars().all()
    )

    return ApiResponse(
        data=[
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "risk_level": t.risk_level,
                "requires_approval": t.requires_approval,
            }
            for t in rows
        ]
    )


@router.post("/", response_model=ApiResponse[dict])
async def create_tool(
        req: ToolCreate,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
):
    t = ToolDefinition(
        tenant_id=user.tenant_id, **req.model_dump(by_alias=True)
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return ApiResponse(data={"id": t.id, "name": t.name})
