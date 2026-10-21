from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.deps import get_current_user
from src.db.session import get_db
from src.models.entities import TraceSpan, User
from src.schemas.common import ApiResponse

router = APIRouter()


@router.get("/{trace_id}", response_model=ApiResponse[dict])
async def get_trace(
        trace_id: str,
        db: AsyncSession = Depends(get_db)
):
    spans = (
        (
            await db.execute(
                select(TraceSpan).where(
                    TraceSpan.trace_id == trace_id
                ).order_by(TraceSpan.created_at)
            )
        ).scalars().all()
    )

    return ApiResponse(
        data={
            "trace_id": trace_id,
            "spans": [
                {
                    "id": s.id,
                    "name": s.name,
                    "kind": s.kind,
                    "status": s.status,
                    "input": s.input,
                    "output": s.output,
                    "latency_ms": s.latency_ms,
                }
                for s in spans
            ],
        }
    )

@router.get("/{trace_id}/tree", response_model=ApiResponse[dict])
async def tree(
        trace_id: str,
        db: AsyncSession = Depends(get_db),
):
    spans = (
        (
            await db.execute(
                select(TraceSpan).where(
                    TraceSpan.trace_id == trace_id
                ).order_by(TraceSpan.created_at)
            )
        ).scalars().all()
    )
    lines = [f"Trace {trace_id}", ""]
    for s in spans:
        lines.append(f"├── {s.name} [{s.kind}] {s.status} {s.latency_ms}ms")
    return ApiResponse(data={"tree": "\n".join(lines)})
