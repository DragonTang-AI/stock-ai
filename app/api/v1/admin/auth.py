"""
app/api/v1/admin/auth.py — 后台登录 / 当前用户 / 修改密码（异步）
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.admin_role import AdminRole
from app.models.admin_user import AdminUser

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def _user_payload(admin: AdminUser, role: AdminRole | None) -> dict:
    return {
        "id": admin.id,
        "username": admin.username,
        "display_name": admin.display_name,
        "role": role.code if role else "viewer",
        "permissions": (role.permissions or []) if role else [],
    }


@router.post("/login")
async def admin_login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AdminUser).where(AdminUser.username == body.username))
    admin = result.scalar_one_or_none()
    if admin is None or not verify_password(body.password, admin.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="账号已禁用")
    admin.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    role = await db.get(AdminRole, admin.role_id)
    token = create_access_token({"sub": str(admin.id), "scope": "admin"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _user_payload(admin, role),
    }


@router.get("/me")
async def admin_me(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    role = await db.get(AdminRole, admin.role_id)
    return _user_payload(admin, role)


@router.post("/change-password")
async def admin_change_password(
    body: ChangePasswordRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.old_password, admin.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    admin.hashed_password = hash_password(body.new_password)
    await db.commit()
    return {"ok": True}
