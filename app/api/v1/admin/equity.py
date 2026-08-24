"""
app/api/v1/admin/equity.py — 权益曲线（P1）

能力：
  GET  /list    有快照的用户列表（按用户聚合：最新权益 / 累计盈亏 / 快照天数）
  GET  /curve   单用户权益曲线（按 snapshot_date 升序，可指定天数窗口）

数据源：equity_snapshots / users
说明：equity_snapshots 每日收盘后记录，当前数据积累中；表空时返回空列表，页面显示空态。
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin, require_permission
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.trading import EquitySnapshot
from app.models.user import User

router = APIRouter()

PERM_VIEW = "equity:view"


def _f(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return v


@router.get("/list")
async def equity_list(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM_VIEW)),
    keyword: str = Query("", description="用户名模糊搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """有快照的用户列表：最新快照 + 快照天数"""
    conds = []
    if keyword:
        conds.append(User.username.ilike(f"%{keyword}%"))

    # 每个用户最新快照日期
    latest_sub = (
        select(
            EquitySnapshot.user_id,
            func.max(EquitySnapshot.snapshot_date).label("latest_date"),
        )
        .group_by(EquitySnapshot.user_id)
        .subquery()
    )
    # 每个用户快照条数
    count_sub = (
        select(
            EquitySnapshot.user_id.label("uid"),
            func.count().label("cnt"),
        )
        .group_by(EquitySnapshot.user_id)
        .subquery()
    )
    # 总行数（用于分页）
    total_q = select(func.count()).select_from(latest_sub)
    if conds:
        total_q = total_q.join(User, User.id == latest_sub.c.user_id).where(*conds)
    total = (await db.execute(total_q)).scalar() or 0

    q = (
        select(
            User.id.label("user_id"),
            User.username,
            EquitySnapshot.snapshot_date.label("latest_date"),
            EquitySnapshot.cash,
            EquitySnapshot.market_value,
            EquitySnapshot.total_equity,
            EquitySnapshot.profit,
            EquitySnapshot.profit_pct,
            count_sub.c.cnt.label("snapshot_count"),
        )
        .join(
            latest_sub,
            (EquitySnapshot.user_id == latest_sub.c.user_id)
            & (EquitySnapshot.snapshot_date == latest_sub.c.latest_date),
        )
        .join(count_sub, count_sub.c.uid == EquitySnapshot.user_id)
        .join(User, User.id == EquitySnapshot.user_id)
        .where(*conds)
        .order_by(desc(EquitySnapshot.snapshot_date), desc(User.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(q)).all()
    items = [
        {
            "user_id": r.user_id,
            "username": r.username,
            "latest_date": _f(r.latest_date),
            "cash": _f(r.cash),
            "market_value": _f(r.market_value),
            "total_equity": _f(r.total_equity),
            "profit": _f(r.profit),
            "profit_pct": _f(r.profit_pct),
            "snapshot_count": r.snapshot_count,
        }
        for r in rows
    ]
    return {"total": total, "items": items}


@router.get("/curve")
async def equity_curve(
    user_id: int = Query(..., description="用户ID"),
    days: int = Query(30, ge=1, le=365, description="天数窗口"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM_VIEW)),
):
    """单用户权益曲线（最近 N 天）"""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    start = date.today() - timedelta(days=days - 1)
    rows = await db.execute(
        select(EquitySnapshot)
        .where(
            EquitySnapshot.user_id == user_id,
            EquitySnapshot.snapshot_date >= start,
        )
        .order_by(EquitySnapshot.snapshot_date)
    )
    snaps = rows.scalars().all()
    return {
        "user": {"id": user.id, "username": user.username},
        "items": [
            {
                "date": s.snapshot_date.isoformat(),
                "cash": float(s.cash),
                "market_value": float(s.market_value),
                "total_equity": float(s.total_equity),
                "profit": float(s.profit),
                "profit_pct": float(s.profit_pct),
            }
            for s in snaps
        ],
    }
