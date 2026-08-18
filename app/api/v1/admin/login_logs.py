"""
app/api/v1/admin/login_logs.py — 登录日志（P1）

登录日志列表（分页/筛选）+ 统计（今日登录、近7日趋势、平台分布）。
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin, require_permission
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.user import User, UserLoginLog

router = APIRouter()

PERM = "customers:view"


@router.get("/list")
async def login_logs_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    platform: str = "",
    client: str = "",
    is_register: str = "",
    start: str = "",
    end: str = "",
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(PERM)),
):
    conds = []
    if keyword:
        like = f"%{keyword}%"
        sub = select(User.id).where(User.username.like(like) | User.nickname.like(like))
        conds.append(UserLoginLog.user_id.in_(sub))
    if platform:
        conds.append(UserLoginLog.platform == platform)
    if client:
        conds.append(UserLoginLog.client == client)
    if is_register in ("true", "false"):
        conds.append(UserLoginLog.is_register == (is_register == "true"))
    if start:
        conds.append(UserLoginLog.login_at >= start)
    if end:
        conds.append(UserLoginLog.login_at <= end + " 23:59:59")

    total = (
        await db.execute(select(func.count()).select_from(UserLoginLog).where(*conds))
    ).scalar_one()

    rows = (
        await db.execute(
            select(UserLoginLog, User.username, User.email)
            .outerjoin(User, User.id == UserLoginLog.user_id)
            .where(*conds)
            .order_by(desc(UserLoginLog.login_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items = [
        {
            "id": r[0].id,
            "user_id": r[0].user_id,
            "username": r[1] or "",
            "email": r[2] or "",
            "login_at": r[0].login_at.isoformat(),
            "ip": r[0].ip or "",
            "user_agent": r[0].user_agent or "",
            "platform": r[0].platform or "",
            "client": r[0].client or "",
            "is_register": r[0].is_register,
        }
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/stats")
async def login_logs_stats(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(PERM)),
):
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    today_total = (
        await db.execute(
            select(func.count()).select_from(UserLoginLog).where(UserLoginLog.login_at >= today_start)
        )
    ).scalar_one()
    today_register = (
        await db.execute(
            select(func.count())
            .select_from(UserLoginLog)
            .where(UserLoginLog.login_at >= today_start, UserLoginLog.is_register.is_(True))
        )
    ).scalar_one()

    trend_rows = (
        await db.execute(
            text(
                """
                select to_char(login_at, 'MM-DD') as day,
                       count(*) as cnt,
                       count(*) filter (where is_register) as reg
                from user_login_logs
                where login_at >= now() - make_interval(days => :days)
                group by day order by day
                """
            ),
            {"days": days},
        )
    ).all()
    trend = [{"day": r[0], "count": r[1], "register": r[2]} for r in trend_rows]

    platform_rows = (
        await db.execute(
            text(
                """
                select coalesce(platform, 'unknown') as platform, count(*) as cnt
                from user_login_logs
                where login_at >= now() - make_interval(days => :days)
                group by platform order by cnt desc
                """
            ),
            {"days": days},
        )
    ).all()
    platform_dist = [{"platform": r[0], "count": r[1]} for r in platform_rows]

    client_rows = (
        await db.execute(
            text(
                """
                select coalesce(client, 'unknown') as client, count(*) as cnt
                from user_login_logs
                where login_at >= now() - make_interval(days => :days)
                group by client order by cnt desc
                """
            ),
            {"days": days},
        )
    ).all()
    client_dist = [{"client": r[0], "count": r[1]} for r in client_rows]

    return {
        "today_total": today_total,
        "today_register": today_register,
        "trend": trend,
        "platform_dist": platform_dist,
        "client_dist": client_dist,
    }
