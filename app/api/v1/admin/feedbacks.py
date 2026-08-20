"""
app/api/v1/admin/feedbacks.py — 用户反馈管理（P1）

反馈列表（分页/多条件筛选）+ 统计 + 回复/状态处理。
回复后自动向 C 端通知中心写入一条通知。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import require_permission
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.agent import Notification
from app.models.feedback import Feedback
from app.models.user import User

router = APIRouter()

VIEW_PERM = "customers:view"
MANAGE_PERM = "customers:manage"

STATUSES = ["pending", "handled", "closed"]


class ReplyIn(BaseModel):
    reply: str


class StatusIn(BaseModel):
    status: str


@router.get("/list")
async def feedbacks_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    ftype: str = "",
    status: str = "",
    start: str = "",
    end: str = "",
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(VIEW_PERM)),
):
    conds = []
    if keyword:
        like = f"%{keyword}%"
        conds.append(
            Feedback.description.like(like)
            | Feedback.contact.like(like)
            | User.username.like(like)
            | User.email.like(like)
        )
    if ftype:
        conds.append(Feedback.type == ftype)
    if status:
        conds.append(Feedback.status == status)
    if start:
        conds.append(Feedback.created_at >= start)
    if end:
        conds.append(Feedback.created_at <= end + " 23:59:59")

    base = (
        select(Feedback, User.username, User.email)
        .outerjoin(User, User.id == Feedback.user_id)
        .where(*conds)
    )

    total = (
        await db.execute(
            select(func.count()).select_from(base.subquery())
        )
    ).scalar_one()

    rows = (
        (
            await db.execute(
                base.order_by(desc(Feedback.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .all()
    )

    items = [
        {
            "id": r[0].id,
            "user_id": r[0].user_id,
            "username": r[1] or "",
            "email": r[2] or "",
            "type": r[0].type,
            "description": r[0].description,
            "contact": r[0].contact or "",
            "status": r[0].status,
            "reply": r[0].reply or "",
            "replied_at": r[0].replied_at.isoformat() if r[0].replied_at else None,
            "replied_by": r[0].replied_by,
            "created_at": r[0].created_at.isoformat(),
        }
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/export")
async def feedbacks_export(
    keyword: str = "",
    ftype: str = "",
    status: str = "",
    start: str = "",
    end: str = "",
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(VIEW_PERM)),
):
    from app.utils.csv_export import csv_response

    conds = []
    if keyword:
        like = f"%{keyword}%"
        conds.append(
            Feedback.description.like(like)
            | Feedback.contact.like(like)
            | User.username.like(like)
            | User.email.like(like)
        )
    if ftype:
        conds.append(Feedback.type == ftype)
    if status:
        conds.append(Feedback.status == status)
    if start:
        conds.append(Feedback.created_at >= start)
    if end:
        conds.append(Feedback.created_at <= end + " 23:59:59")

    base = (
        select(Feedback, User.username, User.email)
        .outerjoin(User, User.id == Feedback.user_id)
        .where(*conds)
    )
    rows = (
        (await db.execute(base.order_by(desc(Feedback.created_at)).limit(10000)))
        .all()
    )

    headers = ["ID", "用户ID", "用户名", "邮箱", "类型", "描述", "联系方式", "状态", "回复内容", "回复人", "回复时间", "提交时间"]
    data = [
        [
            r[0].id,
            r[0].user_id,
            r[1] or "",
            r[2] or "",
            r[0].type,
            r[0].description,
            r[0].contact or "",
            r[0].status,
            r[0].reply or "",
            r[0].replied_by or "",
            r[0].replied_at.isoformat() if r[0].replied_at else "",
            r[0].created_at.isoformat(),
        ]
        for r in rows
    ]
    return csv_response(f"feedbacks_{datetime.now():%Y%m%d%H%M}.csv", headers, data)


@router.get("/stats")
async def feedbacks_stats(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(VIEW_PERM)),
):
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    total = (
        await db.execute(select(func.count()).select_from(Feedback))
    ).scalar_one()
    pending = (
        await db.execute(
            select(func.count()).select_from(Feedback).where(Feedback.status == "pending")
        )
    ).scalar_one()
    today_total = (
        await db.execute(
            select(func.count()).select_from(Feedback).where(Feedback.created_at >= today_start)
        )
    ).scalar_one()

    trend_rows = (
        await db.execute(
            text(
                """
                select to_char(created_at, 'MM-DD') as day, count(*) as cnt
                from feedbacks
                where created_at >= now() - make_interval(days => :days)
                group by day order by day
                """
            ),
            {"days": days},
        )
    ).all()
    trend = [{"day": r[0], "count": r[1]} for r in trend_rows]

    type_rows = (
        await db.execute(
            text(
                """
                select type, count(*) as cnt
                from feedbacks
                where created_at >= now() - make_interval(days => :days)
                group by type order by cnt desc
                """
            ),
            {"days": days},
        )
    ).all()
    type_dist = [{"type": r[0] or "", "count": r[1]} for r in type_rows]

    status_rows = (
        await db.execute(
            text(
                """
                select status, count(*) as cnt
                from feedbacks
                group by status order by cnt desc
                """
            ),
        )
    ).all()
    status_dist = [{"status": r[0] or "", "count": r[1]} for r in status_rows]

    return {
        "total": total,
        "pending": pending,
        "today_total": today_total,
        "trend": trend,
        "type_dist": type_dist,
        "status_dist": status_dist,
    }


@router.post("/{feedback_id}/reply")
async def feedbacks_reply(
    feedback_id: int,
    body: ReplyIn,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(MANAGE_PERM)),
):
    fb = (
        await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    ).scalar_one_or_none()
    if not fb:
        raise HTTPException(status_code=404, detail="反馈不存在")

    reply_text = body.reply.strip()
    if not reply_text:
        raise HTTPException(status_code=400, detail="回复内容不能为空")

    fb.reply = reply_text
    fb.status = "handled"
    fb.replied_at = datetime.now()
    fb.replied_by = admin.id

    # 同步写入 C 端通知中心（agent.notifications）
    db.add(
        Notification(
            user_id=fb.user_id,
            type="feedback_reply",
            title="您的反馈已回复",
            content=f"您的反馈已收到回复：{reply_text}",
            channel="inbox",
        )
    )

    await db.commit()
    return {"ok": True, "id": fb.id, "status": fb.status}


@router.post("/{feedback_id}/status")
async def feedbacks_status(
    feedback_id: int,
    body: StatusIn,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(MANAGE_PERM)),
):
    if body.status not in STATUSES:
        raise HTTPException(status_code=400, detail="无效状态")
    fb = (
        await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    ).scalar_one_or_none()
    if not fb:
        raise HTTPException(status_code=404, detail="反馈不存在")
    fb.status = body.status
    if body.status == "handled" and not fb.replied_at:
        fb.replied_at = datetime.now()
        fb.replied_by = admin.id
    await db.commit()
    return {"ok": True, "id": fb.id, "status": fb.status}
