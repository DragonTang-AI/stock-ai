"""
app/api/v1/admin/changelogs.py — 变更日志管理（P1）

列表/创建/更新/删除。管理员维护版本变更记录，运营/只读可查看。
权限码：changelogs:view（查看）、changelogs:manage（增改删）。
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import require_permission
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.changelog import Changelog
from app.models.operation_log import OperationLog

logger = logging.getLogger(__name__)
router = APIRouter()

VIEW_PERM = "changelogs:view"
MANAGE_PERM = "changelogs:manage"


def _to_dict(c: Changelog) -> dict:
    return {
        "id": c.id,
        "version": c.version,
        "title": c.title,
        "content": c.content,
        "created_at": c.created_at.isoformat() if c.created_at else "",
        "updated_at": c.updated_at.isoformat() if c.updated_at else "",
    }


async def _log(db: AsyncSession, admin: AdminUser, action: str, detail: str = "") -> None:
    db.add(
        OperationLog(
            user_id=admin.id,
            username=admin.username,
            module="changelogs",
            action=action,
            detail=detail[:500],
            ip="",
        )
    )


@router.get("/list")
async def changelog_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(VIEW_PERM)),
):
    conds = []
    if keyword:
        kw = f"%{keyword.strip()}%"
        conds.append(or_(Changelog.version.like(kw), Changelog.title.like(kw)))

    base = select(Changelog).where(*conds)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        (
            await db.execute(
                base.order_by(desc(Changelog.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    items = [_to_dict(c) for c in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


class ChangelogIn(BaseModel):
    version: str = Field(..., description="版本号，如 v1.2.0")
    title: str = Field(..., description="变更标题")
    content: str = Field(..., description="变更内容")


@router.post("/create")
async def changelog_create(
    body: ChangelogIn,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(MANAGE_PERM)),
):
    version = body.version.strip()
    title = body.title.strip()
    content = body.content.strip()
    if not version:
        raise HTTPException(status_code=400, detail="版本号不能为空")
    if not title:
        raise HTTPException(status_code=400, detail="标题不能为空")
    if not content:
        raise HTTPException(status_code=400, detail="变更内容不能为空")

    exists = (
        await db.execute(select(Changelog).where(Changelog.version == version).limit(1))
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail=f"版本号 {version} 已存在")

    c = Changelog(version=version, title=title, content=content)
    db.add(c)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"版本号 {version} 已存在")
    await db.refresh(c)
    await _log(db, admin, "create", f"新增变更日志 {version} {title}")
    await db.commit()
    return {"ok": True, "id": c.id}


class ChangelogUpdate(BaseModel):
    version: str | None = None
    title: str | None = None
    content: str | None = None


@router.put("/{changelog_id}")
async def changelog_update(
    changelog_id: str,
    body: ChangelogUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(MANAGE_PERM)),
):
    c = await db.get(Changelog, changelog_id)
    if not c:
        raise HTTPException(status_code=404, detail="变更日志不存在")

    if body.version is not None:
        version = body.version.strip()
        if not version:
            raise HTTPException(status_code=400, detail="版本号不能为空")
        dup = (
            await db.execute(
                select(Changelog)
                .where(Changelog.version == version, Changelog.id != changelog_id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if dup:
            raise HTTPException(status_code=400, detail=f"版本号 {version} 已存在")
        c.version = version
    if body.title is not None:
        title = body.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="标题不能为空")
        c.title = title
    if body.content is not None:
        content = body.content.strip()
        if not content:
            raise HTTPException(status_code=400, detail="变更内容不能为空")
        c.content = content

    await db.commit()
    await db.refresh(c)
    await _log(db, admin, "update", f"更新变更日志 {c.version} {c.title}")
    await db.commit()
    return {"ok": True, "id": c.id}


@router.delete("/{changelog_id}")
async def changelog_delete(
    changelog_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(MANAGE_PERM)),
):
    c = await db.get(Changelog, changelog_id)
    if not c:
        raise HTTPException(status_code=404, detail="变更日志不存在")
    version = c.version
    title = c.title
    await db.delete(c)
    await db.commit()
    await _log(db, admin, "delete", f"删除变更日志 {version} {title}")
    await db.commit()
    return {"ok": True}
