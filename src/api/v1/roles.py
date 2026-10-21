from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, require_admin
from src.db.session import get_db
from src.models.entities import Role, User, UserRole
from src.schemas.common import ApiResponse

router = APIRouter()


class RoleCreate(BaseModel):
    code: str
    name: str
    permissions: list[str]


class AssignRoleRequest(BaseModel):
    user_id: str
    role_id: str


@router.get("", response_model=ApiResponse[list[dict]])
async def list_roles(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
):
    rows = (
        (
            await db.execute(select(Role).where(Role.tenant_id == user.tenant_id))
        ).scalars().all()
    )
    return ApiResponse(
        data=[
            {"id": r.id, "code": r.code, "name": r.name, "permissions": r.permissions}
            for r in rows
        ]
    )


@router.post("", response_model=ApiResponse[dict])
async def create_role(
        req: RoleCreate,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_admin),
):
    role = Role(
        tenant_id=user.tenant_id,
        code=req.code,
        name=req.name,
        permissions=req.permissions,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return ApiResponse(
        data={"id": role.id, "code": role.code, "permissions": role.permissions}
    )


@router.post("/assign", response_model=ApiResponse[dict])
async def assign_role(
        req: AssignRoleRequest,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_admin),
):
    target = (
        await db.execute(
            select(User).where(User.id == req.user_id, User.tenant_id == user.tenant_id)
        )
    ).scalar_one_or_none()
    role = (
        await db.execute(
            select(Role).where(Role.id == req.role_id, Role.tenant_id == user.tenant_id)
        )
    ).scalar_one_or_none()
    if not target or not role:
        raise HTTPException(404, "user or role not found")
    link = UserRole(user_id=target.id, role_id=role.id)
    db.add(link)
    await db.commit()
    return ApiResponse(data={"user_id": target.id, "role_id": role.id})


@router.get("/me/permissions", response_model=ApiResponse[dict])
async def my_permissions(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
):
    if user.is_admin:
        return ApiResponse(data={"permissions": ["*"], "is_admin": True})
    links = (
        (await db.execute(select(UserRole).where(UserRole.user_id == user.id)))
    ).scalars().all()
    role_ids = [r.role_id for r in links]
    if not role_ids:
        return ApiResponse(data={"permissions": [], "is_admin": False})
    roles = (
        (
            await db.execute(select(Role).where(Role.id.in_(role_ids)))
        ).scalars().all()
    )
    perms = sorted({p for r in roles for p in (r.permissions or [])})
    return ApiResponse(data={"permissions": perms, "is_admin": False})
