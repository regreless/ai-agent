from fastapi import APIRouter
from src.core.config import get_settings
from src.schemas.common import ApiResponse

router = APIRouter()


@router.get("/health", response_model=ApiResponse[dict])
async def health():
    s = get_settings()
    return ApiResponse(
        data={
            "status": "ok",
            "app": s.app_name,
            "llm_provider": s.llm_provider,
            "embedding_provider": s.embedding_provider,
        }
    )
