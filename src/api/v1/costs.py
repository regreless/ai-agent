from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.deps import get_current_user
from src.db.session import get_db
from src.models.entities import CostRecord, User
from src.schemas.common import ApiResponse

router = APIRouter()


@router.get("/summary", response_model=ApiResponse[dict])
async def get_summary(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    rows = (await db.execute(
        select(CostRecord).where(CostRecord.tenant_id == user.tenant_id)
    )).scalars().all()
    total = sum(r.total_cost for r in rows)
    by_agent = defaultdict(float)
    for r in rows:
        by_agent[r.agent_id] += r.total_cost
    return ApiResponse(
        data={
            "total_cost": round(total, 6),
            "records": len(rows),
            "by_agent": {k: round(v, 6) for k, v in by_agent.items()},
        }
    )
