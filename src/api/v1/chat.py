from fastapi import APIRouter, Depends, HTTPException
from openai import APIConnectionError, APIStatusError, APITimeoutError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.db.session import get_db
from src.models.entities import User
from src.schemas.common import ApiResponse
from src.services.workflow.engine import workflow_engine

router = APIRouter()


class ChatRequest(BaseModel):
    agent_id: str
    message: str
    conversation_id: str | None = None


@router.post("", response_model=ApiResponse[dict])
async def chat(
        req: ChatRequest,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    try:
        data = await workflow_engine.run(
            db, user.tenant_id, user.id, req.agent_id, req.message, req.conversation_id
        )
    except APITimeoutError as error:
        raise HTTPException(status_code=504, detail="模型服务响应超时，请稍后重试") from error
    except (APIConnectionError, APIStatusError) as error:
        raise HTTPException(status_code=502, detail="模型服务调用失败，请检查连接及模型配置") from error
    return ApiResponse(data=data)
