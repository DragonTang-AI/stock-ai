"""
app/api/v1/admin/users.py — 后台账号管理（CRUD + 角色分配 + 操作日志，异步）
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin, require_permission
from app.core.database import get_db
from app.core.security import hash_password
from app.models.admin_role import AdminRole
from app.models.admin_user import AdminUser
from app.models.operation_log import OperationLog

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str = ""
    role_id: int


class UserUpdate(BaseModel):
    display_name: str | None = None
    role_id: int | None = None
    password: str | None = None
    is_active: bool | None = None


async def _log(db: AsyncSession, admin: AdminUser, module: str, action: str, detail: str = "") -> None:
    db.add(
        OperationLog(
            user_id=admin.id,
            username=admin.username,
            module=module,
            action=action,
            detail=detail[:500],
            ip="",
        )
    )


@router.get("")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission("users:manage")),
):
    users = (await db.execute(select(AdminUser).order_by(AdminUser.id))).scalars().all()
    roles = {r.id: r for r in (await db.execute(select(AdminRole))).scalars().all()}
    return [
        {
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "role_id": u.role_id,
            "role_code": roles[u.role_id].code if u.role_id in roles else "",
            "is_active": u.is_active,
            "last_login_at": u.last_login_at,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.post("")
async def create_user(
    body: UserCreate,
    admin: AdminUser = Depends(require_permission("users:manage")),
    db: AsyncSession = Depends(get_db),
):
    exists = await db.execute(select(AdminUser).where(AdminUser.username == body.username))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if await db.get(AdminRole, body.role_id) is None:
        raise HTTPException(status_code=400, detail="角色不存在")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    user = AdminUser(
        username=body.username,
        display_name=body.display_name,
        hashed_password=hash_password(body.password),
        role_id=body.role_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await _log(db, admin, "users", "create", f"创建账号 {body.username}")
    await db.commit()
    return {"id": user.id, "username": user.username}


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdate,
    admin: AdminUser = Depends(require_permission("users:manage")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(AdminUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.role_id is not None:
        if await db.get(AdminRole, body.role_id) is None:
            raise HTTPException(status_code=400, detail="角色不存在")
        user.role_id = body.role_id
    if body.password:
        if len(body.password) < 6:
            raise HTTPException(status_code=400, detail="密码至少 6 位")
        user.hashed_password = hash_password(body.password)
    if body.is_active is not None:
        user.is_active = body.is_active
    await db.commit()
    await _log(db, admin, "users", "update", f"更新账号 {user.username}")
    await db.commit()
    return {"ok": True}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    admin: AdminUser = Depends(require_permission("users:manage")),
    db: AsyncSession = Depends(get_db),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")
    user = await db.get(AdminUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    username = user.username
    await db.delete(user)
    await db.commit()
    await _log(db, admin, "users", "delete", f"删除账号 {username}")
    await db.commit()
    return {"ok": True}
