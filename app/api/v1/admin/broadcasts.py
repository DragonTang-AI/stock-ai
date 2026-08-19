"""
app/api/v1/admin/broadcasts.py — 广播通知管理（每日播报，P1）

列表/统计/详情/创建/更新/状态切换/手动生成。
权限码：broadcasts:view（查看）、broadcasts:manage（增改/生成/上下架）。
"""
import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import require_permission
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.broadcast import Broadcast
from app.services.broadcast import generate_daily_broadcast

logger = logging.getLogger(__name__)
router = APIRouter()

VIEW_PERM = "broadcasts:view"
MANAGE_PERM = "broadcasts:manage"

STATUSES = ["published", "draft"]


def _to_dict(b: Broadcast) -> dict:
    return {
        "id": b.id,
        "date": b.date.isoformat() if b.date else "",
        "title": b.title,
        "content": b.content or {"overview": "", "recommendations": [], "risk_warnings": ""},
        "audio_url": b.audio_url,
        "duration": b.duration,
        "status": b.status,
        "created_at": b.created_at.isoformat() if b.created_at else "",
        "updated_at": b.updated_at.isoformat() if b.updated_at else "",
    }


@router.get("/list")
async def broadcast_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    status: str = "",
    date_start: str = "",
    date_end: str = "",
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(VIEW_PERM)),
):
    conds = []
    if keyword:
        conds.append(Broadcast.title.like(f"%{keyword}%"))
    if status:
        if status not in STATUSES:
            raise HTTPException(status_code=400, detail="无效状态")
        conds.append(Broadcast.status == status)
    if date_start:
        conds.append(Broadcast.date >= date_start)
    if date_end:
        conds.append(Broadcast.date <= date_end)

    base = select(Broadcast).where(*conds)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        (
            await db.execute(
                base.order_by(desc(Broadcast.date), desc(Broadcast.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    items = [_to_dict(b) for b in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/stats")
async def broadcast_stats(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(VIEW_PERM)),
):
    total = (await db.execute(select(func.count()).select_from(Broadcast))).scalar_one()
    published = (
        await db.execute(
            select(func.count()).select_from(Broadcast).where(Broadcast.status == "published")
        )
    ).scalar_one()
    draft = (
        await db.execute(
            select(func.count()).select_from(Broadcast).where(Broadcast.status == "draft")
        )
    ).scalar_one()

    trend_rows = (
        await db.execute(
            text(
                """
                select to_char(date, 'MM-DD') as day, count(*) as cnt
                from broadcasts
                where date >= (current_date - make_interval(days => :days))
                group by day order by day
                """
            ),
            {"days": days},
        )
    ).all()
    trend = [{"day": r[0], "count": r[1]} for r in trend_rows]

    latest = (
        await db.execute(select(Broadcast).order_by(desc(Broadcast.date)).limit(1))
    ).scalar_one_or_none()

    return {
        "total": total,
        "published": published,
        "draft": draft,
        "trend": trend,
        "latest_date": latest.date.isoformat() if latest else None,
        "latest_status": latest.status if latest else None,
    }


@router.get("/{broadcast_id}")
async def broadcast_detail(
    broadcast_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(VIEW_PERM)),
):
    b = await db.get(Broadcast, broadcast_id)
    if not b:
        raise HTTPException(status_code=404, detail="播报不存在")
    return _to_dict(b)


class BroadcastIn(BaseModel):
    date: str = Field(..., description="日期 YYYY-MM-DD")
    title: str = ""
    content: dict = Field(default_factory=dict)
    audio_url: str | None = None
    duration: int | None = None
    status: str = "published"


@router.post("/create")
async def broadcast_create(
    body: BroadcastIn,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(MANAGE_PERM)),
):
    try:
        target_date = date.fromisoformat(body.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式无效，应为 YYYY-MM-DD")

    exists = (
        await db.execute(select(Broadcast).where(Broadcast.date == target_date).limit(1))
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="该日期播报已存在")

    if body.status not in STATUSES:
        raise HTTPException(status_code=400, detail="无效状态")

    b = Broadcast(
        date=target_date,
        title=body.title.strip() or f"{target_date.strftime('%m月%d日')} 每日播报",
        content=body.content or {"overview": "", "recommendations": [], "risk_warnings": ""},
        audio_url=body.audio_url,
        duration=body.duration,
        status=body.status,
    )
    db.add(b)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="该日期播报已存在")
    await db.refresh(b)
    return {"ok": True, "id": b.id}


class BroadcastUpdate(BaseModel):
    title: str | None = None
    content: dict | None = None
    audio_url: str | None = None
    duration: int | None = None
    status: str | None = None


@router.put("/{broadcast_id}")
async def broadcast_update(
    broadcast_id: str,
    body: BroadcastUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(MANAGE_PERM)),
):
    b = await db.get(Broadcast, broadcast_id)
    if not b:
        raise HTTPException(status_code=404, detail="播报不存在")

    if body.title is not None:
        title = body.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="标题不能为空")
        b.title = title
    if body.content is not None:
        b.content = body.content
    if body.audio_url is not None:
        b.audio_url = body.audio_url or None
    if body.duration is not None:
        if body.duration < 0:
            raise HTTPException(status_code=400, detail="时长不能为负")
        b.duration = body.duration
    if body.status is not None:
        if body.status not in STATUSES:
            raise HTTPException(status_code=400, detail="无效状态")
        b.status = body.status

    await db.commit()
    await db.refresh(b)
    return {"ok": True, "id": b.id, "status": b.status}


@router.post("/{broadcast_id}/status")
async def broadcast_status(
    broadcast_id: str,
    body: BroadcastUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(MANAGE_PERM)),
):
    if body.status not in STATUSES:
        raise HTTPException(status_code=400, detail="无效状态")
    b = await db.get(Broadcast, broadcast_id)
    if not b:
        raise HTTPException(status_code=404, detail="播报不存在")
    b.status = body.status
    await db.commit()
    return {"ok": True, "id": b.id, "status": b.status}


class GenerateIn(BaseModel):
    date: str | None = None


@router.post("/generate")
async def broadcast_generate(
    body: GenerateIn,
    admin: AdminUser = Depends(require_permission(MANAGE_PERM)),
):
    """手动触发某日播报生成（复用 C 端生成服务，自动拉行情+LLM 生成并 upsert）"""
    target_date = None
    if body.date:
        try:
            target_date = date.fromisoformat(body.date)
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式无效，应为 YYYY-MM-DD")
    try:
        b = await generate_daily_broadcast(target_date)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"Generate broadcast failed: {e}")
        raise HTTPException(status_code=500, detail="播报生成失败，请稍后重试")
    return {"ok": True, "id": b.id, "date": b.date.isoformat(), "status": b.status}
