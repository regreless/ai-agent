from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, verify_password
from src.db.session import get_db
from src.models.entities import User
from src.schemas.auth import LoginRequest
from src.schemas.common import ApiResponse
from src.api.deps import get_current_user

router = APIRouter()


@router.post("/login", response_model=ApiResponse[dict])
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()
    if not user or not user.is_active or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token(user.id)
    return ApiResponse(
        data={
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "tenant_id": user.tenant_id,
                "is_admin": user.is_admin,
            }
        })


@router.post("/me", response_model=ApiResponse[dict])
async def me(user: User = Depends(get_current_user)):
    return ApiResponse(
        data={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "tenant_id": user.tenant_id,
            "is_admin": user.is_admin,
        }
    )
