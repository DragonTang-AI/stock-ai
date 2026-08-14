"""
app/api/v1/admin/deps.py — 后台鉴权与权限依赖（异步）
"""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_token
from app.models.admin_role import AdminRole
from app.models.admin_user import AdminUser


async def get_current_admin(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """从 Authorization header 解析 admin JWT，返回当前管理员"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    token = auth_header[7:]
    payload = verify_token(token)
    if payload is None or payload.get("scope") != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效凭证")
    try:
        admin_id = int(payload.get("sub", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效凭证")
    admin = await db.get(AdminUser, admin_id)
    if admin is None or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不可用")
    return admin


def require_permission(permission: str):
    """权限码校验依赖工厂"""

    async def checker(
        admin: AdminUser = Depends(get_current_admin),
        db: AsyncSession = Depends(get_db),
    ) -> AdminUser:
        role = await db.get(AdminRole, admin.role_id)
        if role is None or permission not in (role.permissions or []):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
        return admin

    return checker
