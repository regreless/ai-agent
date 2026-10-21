from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.api.deps import get_current_user
from src.db.session import get_db
from src.models.entities import ModelProvider, User
from src.schemas.common import ApiResponse

router = APIRouter()


class ModelCreate(BaseModel):
    provider: str
    model_name: str
    display_name: str
    base_url: str = ""
    input_price_per_1k: float = 0
    output_price_per_1k: float = 0


@router.get("", response_model=ApiResponse[list[dict]])
async def list_models(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
):
    rows = (
        (await db.execute(select(ModelProvider).where(ModelProvider.tenant_id == user.tenant_id)))
    ).scalars().all()
    return ApiResponse(
        data=[
            {
                "id": r.id,
                "provider": r.provider,
                "model_name": r.model_name,
                "display_name": r.display_name,
                "enabled": r.enabled,
            }
            for r in rows
        ]
    )


@router.post("", response_model=ApiResponse[dict])
async def create_model(
        req: ModelCreate,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    m = ModelProvider(tenant_id=user.tenant_id, **req.model_dump())
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return ApiResponse(data={"id": m.id, "provider": m.provider, "model_name": m.model_name})
