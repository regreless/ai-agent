from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import require_admin
from src.core.security import hash_password
from src.db.session import get_db
from src.models.entities import User, UserRole
from src.schemas.common import ApiResponse

router = APIRouter()


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = Field(default=None, max_length=255)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    password: str | None = Field(default=None, min_length=8, max_length=72)
    is_active: bool | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str | None) -> str | None:
        if password is not None and len(password.encode("utf-8")) > 72:
            raise ValueError("password must not exceed 72 bytes")
        return password

    @model_validator(mode="after")
    def reject_null_fields(self):
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} must not be null")
        return self


class UserCreateRequest(UserUpdateRequest):
    email: EmailStr = Field(max_length=255)
    name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=72)
    is_active: bool = True


async def get_tenant_user(db: AsyncSession, user_id: str, tenant_id: str) -> User:
    target_user = (
        await db.execute(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    ).scalar_one_or_none()
    if not target_user:
        raise HTTPException(404, "user not found")
    return target_user


async def validate_email(db: AsyncSession, email: str, user_id: str | None = None):
    query = select(User).where(User.email == email)
    if user_id is not None:
        query = query.where(User.id != user_id)
    if (await db.execute(query)).scalar_one_or_none():
        raise HTTPException(409, "email already exists")


async def serialize_users(db: AsyncSession, users: list[User]) -> list[dict]:
    if not users:
        return []
    user_ids = [user.id for user in users]
    links = (await db.execute(select(UserRole).where(UserRole.user_id.in_(user_ids)))).scalars().all()
    role_map = {user_id: set() for user_id in user_ids}
    for link in links:
        role_map[link.user_id].add(link.role_id)
    return [
        {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "tenant_id": user.tenant_id,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "role_ids": sorted(role_map[user.id]),
        }
        for user in users
    ]


@router.post("", response_model=ApiResponse[dict], summary="新建用户")
async def create_user(
        req: UserCreateRequest,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_admin),
):
    """在当前租户创建普通用户，角色通过 /roles/assign 接口分配。"""
    await validate_email(db, str(req.email))
    new_user = User(
        tenant_id=user.tenant_id,
        email=str(req.email),
        name=req.name,
        hashed_password=hash_password(req.password),
        is_admin=False,
        is_active=req.is_active,
    )
    try:
        db.add(new_user)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        await validate_email(db, str(req.email))
        raise
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=(await serialize_users(db, [new_user]))[0])


@router.get("", response_model=ApiResponse[list[dict]], summary="查询用户列表")
async def list_users(
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=200),
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_admin),
):
    users = (
        await db.execute(
            select(User).where(User.tenant_id == user.tenant_id)
            .order_by(User.created_at, User.id).offset(offset).limit(limit)
        )
    ).scalars().all()
    return ApiResponse(data=await serialize_users(db, users))


@router.get("/{user_id}", response_model=ApiResponse[dict], summary="查询用户详情")
async def get_user(
        user_id: str,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_admin),
):
    target_user = await get_tenant_user(db, user_id, user.tenant_id)
    return ApiResponse(data=(await serialize_users(db, [target_user]))[0])


@router.patch("/{user_id}", response_model=ApiResponse[dict], summary="修改用户")
async def update_user(
        user_id: str,
        req: UserUpdateRequest,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_admin),
):
    """只修改传入的用户字段。"""
    target_user = await get_tenant_user(db, user_id, user.tenant_id)
    if target_user.id == user.id and req.is_active is False:
        raise HTTPException(400, "cannot disable yourself")
    if req.email is not None:
        await validate_email(db, str(req.email), user_id)
    changes = req.model_dump(exclude_unset=True, exclude={"password"})
    if req.password is not None:
        changes["hashed_password"] = hash_password(req.password)
    email = str(req.email) if req.email is not None else target_user.email
    try:
        for field_name, field_value in changes.items():
            setattr(target_user, field_name, field_value)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        await validate_email(db, email, user_id)
        raise
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data=(await serialize_users(db, [target_user]))[0])


@router.delete("/{user_id}", response_model=ApiResponse[dict], summary="删除用户")
async def delete_user(
        user_id: str,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_admin),
):
    await get_tenant_user(db, user_id, user.tenant_id)
    if user_id == user.id:
        raise HTTPException(400, "cannot delete yourself")
    try:
        await db.execute(delete(UserRole).where(UserRole.user_id == user_id))
        await db.execute(delete(User).where(User.id == user_id, User.tenant_id == user.tenant_id))
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return ApiResponse(data={"user_id": user_id})
