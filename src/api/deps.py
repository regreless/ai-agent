from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import decode_access_token
from src.db.session import get_db
from src.models.entities import User, Role, UserRole

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
        db: AsyncSession = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user


def require_permission(permission: str):
    async def checker(
            user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
    ) -> User:
        if user.is_admin:
            return user
        links = (
            (await db.execute(select(UserRole).where(UserRole.user_id == user.id))).scalars().all()
        )
        role_ids = [item.role_id for item in links]
        if not role_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"缺少权限：{permission}"
            )
        roles = (
            (await db.execute(select(Role).where(Role.id.in_(role_ids)))).scalars().all()
        )
        perms = {p for r in roles for p in (r.permissions or [])}
        if "*" not in perms and permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"缺少权限：{permission}"
            )
        return user

    return checker