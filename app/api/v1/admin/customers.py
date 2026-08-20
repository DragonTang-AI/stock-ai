"""
app/api/v1/admin/customers.py — 前端 C 端用户管理（只读为主 + 禁用/启用）

能力：
  GET  /list            用户列表（关键词/状态/注册时间区间/分页，含资产/积分/活跃聚合列）
  GET  /stats           用户统计（总用户/区间新增/今日DAU/本月MAU/按天趋势）
  GET  /{user_id}       用户详情 360 视图（信息/资产/订单/信号/持仓/登录日志）
  POST /{user_id}/toggle-active  禁用/启用用户

数据源：users / accounts / user_points / orders / signals / positions / user_login_logs
活跃口径：user_login_logs（C 端登录/注册时写入），DAU = 当日登录去重用户数，MAU = 当月。
"""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin, require_permission
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.points import UserPoints
from app.models.signals import Signal
from app.models.trading import Account, Order, Position
from app.models.user import User, UserLoginLog

router = APIRouter()

PERM_VIEW = "customers:view"
PERM_MANAGE = "customers:manage"


def _f(v):
    from decimal import Decimal

    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return v


async def _batch_login_agg(db, user_ids):
    """批量取每个用户最近登录时间与登录次数"""
    if not user_ids:
        return {}
    rows = (
        await db.execute(
            select(
                UserLoginLog.user_id,
                func.max(UserLoginLog.login_at).label("last_login_at"),
                func.count().label("login_count"),
            )
            .where(UserLoginLog.user_id.in_(user_ids))
            .group_by(UserLoginLog.user_id)
        )
    ).all()
    return {r.user_id: {"last_login_at": _f(r.last_login_at), "login_count": r.login_count} for r in rows}


async def _batch_points(db, user_ids):
    if not user_ids:
        return {}
    rows = (
        await db.execute(select(UserPoints).where(UserPoints.user_id.in_(user_ids)))
    ).scalars().all()
    return {r.user_id: r.balance for r in rows}


async def _batch_orders_count(db, user_ids):
    if not user_ids:
        return {}
    rows = (
        await db.execute(
            select(Order.user_id, func.count().label("cnt"))
            .where(Order.user_id.in_(user_ids))
            .group_by(Order.user_id)
        )
    ).all()
    return {r.user_id: r.cnt for r in rows}


async def _batch_signals_count(db, user_ids):
    if not user_ids:
        return {}
    rows = (
        await db.execute(
            select(Signal.user_id, func.count().label("cnt"))
            .where(Signal.user_id.in_(user_ids))
            .group_by(Signal.user_id)
        )
    ).all()
    return {r.user_id: r.cnt for r in rows}


async def _batch_accounts(db, user_ids):
    if not user_ids:
        return {}
    rows = (
        await db.execute(
            select(Account.user_id, Account.market, Account.balance).where(
                Account.user_id.in_(user_ids)
            )
        )
    ).all()
    agg: dict = {}
    for r in rows:
        item = agg.setdefault(r.user_id, {"markets": [], "total_balance": 0.0})
        item["markets"].append({"market": r.market, "balance": _f(r.balance)})
        item["total_balance"] += float(r.balance or 0)
    for item in agg.values():
        item["total_balance"] = round(item["total_balance"], 2)
    return agg


@router.get("/list")
async def customer_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", description="用户名/邮箱模糊搜索"),
    status: str = Query("", description="active / disabled / 空=全部"),
    start_date: str = Query("", description="注册开始日期 YYYY-MM-DD"),
    end_date: str = Query("", description="注册结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM_VIEW)),
):
    conds = []
    if keyword:
        like = f"%{keyword}%"
        conds.append((User.username.ilike(like)) | (User.email.ilike(like)))
    if status == "active":
        conds.append(User.is_active.is_(True))
    elif status == "disabled":
        conds.append(User.is_active.is_(False))
    if start_date:
        conds.append(User.created_at >= datetime.fromisoformat(f"{start_date}T00:00:00"))
    if end_date:
        conds.append(User.created_at < datetime.fromisoformat(f"{end_date}T00:00:00") + timedelta(days=1))

    base = select(User)
    for c in conds:
        base = base.where(c)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    rows = (
        (await db.execute(
            base.order_by(desc(User.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        ))
        .scalars()
        .all()
    )
    user_ids = [u.id for u in rows]
    login_agg = await _batch_login_agg(db, user_ids)
    points_agg = await _batch_points(db, user_ids)
    orders_agg = await _batch_orders_count(db, user_ids)
    signals_agg = await _batch_signals_count(db, user_ids)
    accounts_agg = await _batch_accounts(db, user_ids)

    items = []
    for u in rows:
        items.append(
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "is_active": u.is_active,
                "created_at": _f(u.created_at),
                "last_login_at": login_agg.get(u.id, {}).get("last_login_at"),
                "login_count": login_agg.get(u.id, {}).get("login_count", 0),
                "points": points_agg.get(u.id, 0),
                "total_balance": accounts_agg.get(u.id, {}).get("total_balance", 0.0),
                "markets": accounts_agg.get(u.id, {}).get("markets", []),
                "orders_count": orders_agg.get(u.id, 0),
                "signals_count": signals_agg.get(u.id, 0),
            }
        )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/export")
async def customer_export(
    keyword: str = "",
    status: str = "",
    start_date: str = "",
    end_date: str = "",
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM_VIEW)),
):
    from app.utils.csv_export import csv_response

    conds = []
    if keyword:
        like = f"%{keyword}%"
        conds.append((User.username.ilike(like)) | (User.email.ilike(like)))
    if status == "active":
        conds.append(User.is_active.is_(True))
    elif status == "disabled":
        conds.append(User.is_active.is_(False))
    if start_date:
        conds.append(User.created_at >= datetime.fromisoformat(f"{start_date}T00:00:00"))
    if end_date:
        conds.append(User.created_at < datetime.fromisoformat(f"{end_date}T00:00:00") + timedelta(days=1))

    base = select(User)
    for c in conds:
        base = base.where(c)
    rows = (
        (await db.execute(base.order_by(desc(User.created_at)).limit(10000)))
        .scalars()
        .all()
    )
    user_ids = [u.id for u in rows]
    login_agg = await _batch_login_agg(db, user_ids)
    points_agg = await _batch_points(db, user_ids)
    orders_agg = await _batch_orders_count(db, user_ids)
    signals_agg = await _batch_signals_count(db, user_ids)
    accounts_agg = await _batch_accounts(db, user_ids)

    headers = ["ID", "用户名", "邮箱", "状态", "注册时间", "最近登录", "登录次数", "积分", "总资产", "订单数", "信号数"]
    data = []
    for u in rows:
        data.append([
            u.id,
            u.username,
            u.email or "",
            "正常" if u.is_active else "已禁用",
            _f(u.created_at) or "",
            login_agg.get(u.id, {}).get("last_login_at") or "",
            login_agg.get(u.id, {}).get("login_count", 0),
            points_agg.get(u.id, 0),
            accounts_agg.get(u.id, {}).get("total_balance", 0.0),
            orders_agg.get(u.id, 0),
            signals_agg.get(u.id, 0),
        ])
    return csv_response(f"customers_{datetime.now():%Y%m%d%H%M}.csv", headers, data)


@router.get("/stats")
async def customer_stats(
    start_date: str = Query("", description="开始日期 YYYY-MM-DD，默认近30天"),
    end_date: str = Query("", description="结束日期 YYYY-MM-DD，默认今天"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM_VIEW)),
):
    today = date.today()
    try:
        end = date.fromisoformat(end_date) if end_date else today
        start = date.fromisoformat(start_date) if start_date else end - timedelta(days=29)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")
    if start > end:
        start, end = end, start
    start_dt = datetime(start.year, start.month, start.day)
    end_exclusive = datetime(end.year, end.month, end.day) + timedelta(days=1)

    # 总用户（全量）
    total_users = (
        await db.execute(select(func.count()).select_from(User))
    ).scalar() or 0

    # 区间新增
    period_new = (
        await db.execute(
            select(func.count()).select_from(User).where(User.created_at >= start_dt, User.created_at < end_exclusive)
        )
    ).scalar() or 0

    # 今日 DAU
    dau_today = (
        await db.execute(
            select(func.count(func.distinct(UserLoginLog.user_id))).where(
                UserLoginLog.login_at >= datetime(today.year, today.month, today.day),
                UserLoginLog.login_at < datetime(today.year, today.month, today.day) + timedelta(days=1),
            )
        )
    ).scalar() or 0

    # 本月 MAU（自然月）
    month_start = datetime(today.year, today.month, 1)
    month_end_exclusive = (month_start + timedelta(days=32)).replace(day=1)
    mau = (
        await db.execute(
            select(func.count(func.distinct(UserLoginLog.user_id))).where(
                UserLoginLog.login_at >= month_start,
                UserLoginLog.login_at < month_end_exclusive,
            )
        )
    ).scalar() or 0

    # 区间按天趋势：新增 / DAU
    new_rows = (
        await db.execute(
            select(func.date(User.created_at).label("d"), func.count().label("c"))
            .where(User.created_at >= start_dt, User.created_at < end_exclusive)
            .group_by("d")
        )
    ).all()
    dau_rows = (
        await db.execute(
            select(func.date(UserLoginLog.login_at).label("d"), func.count(func.distinct(UserLoginLog.user_id)).label("c"))
            .where(UserLoginLog.login_at >= start_dt, UserLoginLog.login_at < end_exclusive)
            .group_by("d")
        )
    ).all()
    new_map = {str(r.d): r.c for r in new_rows}
    dau_map = {str(r.d): r.c for r in dau_rows}

    trend = []
    d = start
    while d <= end:
        ds = d.isoformat()
        trend.append({"date": ds, "new_users": new_map.get(ds, 0), "dau": dau_map.get(ds, 0)})
        d += timedelta(days=1)

    return {
        "total_users": total_users,
        "period_new_users": period_new,
        "dau_today": dau_today,
        "mau": mau,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "trend": trend,
    }


@router.get("/{user_id}")
async def customer_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM_VIEW)),
):
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    points = (
        await db.execute(select(UserPoints).where(UserPoints.user_id == user_id))
    ).scalar_one_or_none()
    accounts = (
        await db.execute(select(Account).where(Account.user_id == user_id))
    ).scalars().all()
    orders = (
        await db.execute(
            select(Order).where(Order.user_id == user_id).order_by(desc(Order.created_at)).limit(20)
        )
    ).scalars().all()
    signals = (
        await db.execute(
            select(Signal).where(Signal.user_id == user_id).order_by(desc(Signal.created_at)).limit(20)
        )
    ).scalars().all()
    positions = (
        await db.execute(select(Position).where(Position.user_id == user_id))
    ).scalars().all()
    login_logs = (
        await db.execute(
            select(UserLoginLog).where(UserLoginLog.user_id == user_id).order_by(desc(UserLoginLog.login_at)).limit(30)
        )
    ).scalars().all()

    def _order_dict(o):
        return {c: _f(getattr(o, c)) for c in ("id", "symbol", "side", "qty", "price", "status", "created_at") if hasattr(o, c)}

    def _signal_dict(s):
        return {
            "id": s.id,
            "symbol": getattr(s, "symbol", None),
            "engine": getattr(s, "engine", None),
            "direction": getattr(s, "direction", getattr(s, "side", None)),
            "price": _f(getattr(s, "price", None)),
            "created_at": _f(getattr(s, "created_at", None)),
        }

    def _position_dict(p):
        return {
            "symbol": getattr(p, "symbol", None),
            "market": getattr(p, "market", None),
            "qty": _f(getattr(p, "qty", None)),
            "avg_price": _f(getattr(p, "avg_price", None)),
            "updated_at": _f(getattr(p, "updated_at", None)),
        }

    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": _f(user.created_at),
            "updated_at": _f(user.updated_at),
        },
        "points": {
            "balance": points.balance if points else 0,
            "total_earned": points.total_earned if points else 0,
            "total_spent": points.total_spent if points else 0,
        },
        "accounts": [
            {"market": a.market, "balance": _f(a.balance), "updated_at": _f(a.updated_at)}
            for a in accounts
        ],
        "total_balance": round(sum(float(a.balance or 0) for a in accounts), 2),
        "orders": [_order_dict(o) for o in orders],
        "signals": [_signal_dict(s) for s in signals],
        "positions": [_position_dict(p) for p in positions],
        "login_logs": [
            {
                "login_at": _f(log.login_at),
                "ip": log.ip,
                "platform": log.platform,
                "client": log.client,
                "is_register": log.is_register,
            }
            for log in login_logs
        ],
    }


@router.post("/{user_id}/toggle-active")
async def customer_toggle_active(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM_MANAGE)),
):
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.is_active = not user.is_active
    await db.commit()
    return {"id": user.id, "is_active": user.is_active}
