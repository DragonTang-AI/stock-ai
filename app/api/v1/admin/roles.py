"""
app/api/v1/admin/roles.py — 后台角色管理（RBAC，异步）
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import require_permission
from app.core.database import get_db
from app.models.admin_role import AdminRole
from app.models.admin_user import AdminUser

router = APIRouter()


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None


@router.get("")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission("users:manage")),
):
    roles = (await db.execute(select(AdminRole).order_by(AdminRole.id))).scalars().all()
    return [
        {
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "description": r.description,
            "permissions": r.permissions or [],
        }
        for r in roles
    ]


@router.put("/{role_id}")
async def update_role(
    role_id: int,
    body: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission("roles:manage")),
):
    role = await db.get(AdminRole, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if body.name is not None:
        role.name = body.name
    if body.description is not None:
        role.description = body.description
    if body.permissions is not None:
        role.permissions = body.permissions
    await db.commit()
    return {"ok": True}
