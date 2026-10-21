from sqlalchemy.ext.asyncio import AsyncSession
from src.models.entities import TraceSpan


class TraceService:
    async def add_span(
            self,
            db: AsyncSession,
            trace_id: str,
            run_id: str,
            name: str,
            kind: str,
            input: dict | None = None,
            output: dict | None = None,
            latency_ms: int = 0,
    ):
        span = TraceSpan(
            trace_id=trace_id,
            run_id=run_id,
            name=name,
            kind=kind,
            input=input or {},
            output=output or {},
            latency_ms=latency_ms,
        )
        db.add(span)
        await db.flush()
        return span


trace_service = TraceService()
