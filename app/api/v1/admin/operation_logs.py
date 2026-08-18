"""
app/api/v1/admin/operation_logs.py — 操作日志增强（P1）

操作日志列表（分页/多条件筛选）+ 统计（今日/近7天趋势、模块分布、操作人 Top）。
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import require_permission
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.operation_log import OperationLog

router = APIRouter()

PERM = "dashboard:view"


@router.get("/list")
async def operation_logs_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    module: str = "",
    ip: str = "",
    start: str = "",
    end: str = "",
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(PERM)),
):
    conds = []
    if keyword:
        like = f"%{keyword}%"
        conds.append(
            OperationLog.username.like(like)
            | OperationLog.action.like(like)
            | OperationLog.detail.like(like)
        )
    if module:
        conds.append(OperationLog.module == module)
    if ip:
        conds.append(OperationLog.ip.like(f"%{ip}%"))
    if start:
        conds.append(OperationLog.created_at >= start)
    if end:
        conds.append(OperationLog.created_at <= end + " 23:59:59")

    total = (
        await db.execute(
            select(func.count()).select_from(OperationLog).where(*conds)
        )
    ).scalar_one()

    rows = (
        (
            await db.execute(
                select(OperationLog)
                .where(*conds)
                .order_by(desc(OperationLog.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    items = [
        {
            "id": r.id,
            "user_id": r.user_id,
            "username": r.username,
            "module": r.module,
            "action": r.action,
            "detail": r.detail,
            "ip": r.ip,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/stats")
async def operation_logs_stats(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(PERM)),
):
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_total = (
        await db.execute(
            select(func.count())
            .select_from(OperationLog)
            .where(OperationLog.created_at >= today_start)
        )
    ).scalar_one()

    trend_rows = (
        await db.execute(
            text(
                """
                select to_char(created_at, 'MM-DD') as day, count(*) as cnt
                from operation_logs
                where created_at >= now() - make_interval(days => :days)
                group by day order by day
                """
            ),
            {"days": days},
        )
    ).all()
    trend = [{"day": r[0], "count": r[1]} for r in trend_rows]

    module_rows = (
        await db.execute(
            text(
                """
                select module, count(*) as cnt
                from operation_logs
                where created_at >= now() - make_interval(days => :days)
                group by module order by cnt desc
                """
            ),
            {"days": days},
        )
    ).all()
    module_dist = [{"module": r[0] or "", "count": r[1]} for r in module_rows]

    user_rows = (
        await db.execute(
            text(
                """
                select username, count(*) as cnt
                from operation_logs
                where created_at >= now() - make_interval(days => :days)
                group by username order by cnt desc limit 10
                """
            ),
            {"days": days},
        )
    ).all()
    user_dist = [{"username": r[0] or "", "count": r[1]} for r in user_rows]

    return {
        "today_total": today_total,
        "trend": trend,
        "module_dist": module_dist,
        "user_dist": user_dist,
    }
