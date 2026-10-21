from fastapi import HTTPException, status
from src.models.entities import User


def require_permission(user: User, permission: str):
    if user.is_admin:
        return True
    # 简化版：生产可查 user_roles/role_permissions
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'缺少权限：{permission}')
