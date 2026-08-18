"""
app/api/v1/admin/workspace.py — 后台工作台（M5，只读聚合）

一次请求聚合登录后首页所需数据：
- 系统健康：admin/stockai 服务在线、调度器状态、托管会话数
- 运营速览：总用户/今日新增、交易员/活跃雇佣、今日信号/成交/盈亏、待处理反馈
- 待办提醒：初始密码风险、今日推荐缺失、异常信号
- 最近动态：最近信号、最近订单、最近登录用户
"""
import os
from datetime import date, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import case, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin, require_permission
from app.core.database import get_db
from app.core.security import verify_password
from app.models.admin_user import AdminUser
from app.models.agent import AgentTrader, UserAgent
from app.models.daily_pick import DailyPick
from app.models.signals import Signal
from app.models.trading import Order, Trade
from app.models.user import User, UserLoginLog

router = APIRouter()

PERM = "dashboard:view"

INTERNAL_BASE = os.getenv("ADMIN_INTERNAL_BASE", "http://127.0.0.1:8000")
INTERNAL_TOKEN = os.getenv("ADMIN_INTERNAL_TOKEN", "stockai_admin_internal_2026")
DEFAULT_PASSWORD = "KeTPCFsrua6Xqw"


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


async def _fetch_internal():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                f"{INTERNAL_BASE}/api/v1/internal/hosted/overview",
                headers={"X-Internal-Token": INTERNAL_TOKEN},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return None


@router.get("/summary")
async def workspace_summary(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(PERM)),
):
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    now = datetime.now()

    # ── 运营速览 ──
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    new_users_today = (
        await db.execute(
            select(func.count(User.id)).where(User.created_at >= today_start)
        )
    ).scalar() or 0
    total_agents = (
        await db.execute(select(func.count(AgentTrader.id)))
    ).scalar() or 0
    hire_active = (
        await db.execute(
            select(func.count(UserAgent.id)).where(UserAgent.status == "active")
        )
    ).scalar() or 0
    signal_today = (
        await db.execute(
            select(func.count(Signal.id)).where(Signal.created_at >= today_start)
        )
    ).scalar() or 0
    error_signals_today = (
        await db.execute(
            select(func.count(Signal.id)).where(
                Signal.created_at >= today_start, Signal.status == "ERROR"
            )
        )
    ).scalar() or 0
    trade_row = (
        await db.execute(
            select(
                func.count(Trade.id),
                func.coalesce(func.sum(Trade.amount), 0),
            ).where(Trade.trade_date == today)
        )
    ).one()
    pnl_row = (
        await db.execute(
            select(
                func.coalesce(
                    func.sum(case((Trade.side == "BUY", Trade.amount * -1), else_=Trade.amount)),
                    0,
                )
            ).where(Trade.trade_date == today)
        )
    ).one()
    feedback_pending = (
        await db.execute(text("select count(*) from feedbacks"))
    ).scalar() or 0

    # ── 系统健康 ──
    internal = await _fetch_internal()
    scheduler = (internal or {}).get("scheduler") or {}
    engine_active = (internal or {}).get("active_count", 0)

    # ── 待办 ──
    todos = []
    admin_row = (
        await db.execute(
            select(AdminUser).where(AdminUser.id == admin.id)
        )
    ).scalar_one_or_none()
    if admin_row and verify_password(DEFAULT_PASSWORD, admin_row.hashed_password):
        todos.append({
            "key": "default_password",
            "level": "danger",
            "title": "当前账号仍在使用初始密码",
            "desc": "为保障后台安全，请尽快修改管理员密码。",
        })
    picks_today = (
        await db.execute(
            select(func.count(DailyPick.id)).where(DailyPick.trade_date == today.isoformat())
        )
    ).scalar() or 0
    if picks_today == 0:
        todos.append({
            "key": "no_picks_today",
            "level": "warning",
            "title": "今日推荐尚未生成",
            "desc": "调度器今日未产出每日推荐，请检查调度状态。",
        })
    if error_signals_today > 0:
        todos.append({
            "key": "signal_errors",
            "level": "warning",
            "title": f"今日有 {error_signals_today} 条异常信号",
            "desc": "部分信号执行失败，请到 Agent 监控核对。",
        })
    if feedback_pending > 0:
        todos.append({
            "key": "feedback_pending",
            "level": "info",
            "title": f"待处理用户反馈 {feedback_pending} 条",
            "desc": "反馈管理模块上线后即可处理。",
        })

    # ── 最近动态 ──
    recent_signals = (
        await db.execute(
            select(Signal)
            .order_by(Signal.created_at.desc())
            .limit(8)
        )
    ).scalars().all()
    recent_orders = (
        await db.execute(
            select(Order)
            .order_by(Order.created_at.desc())
            .limit(8)
        )
    ).scalars().all()
    recent_logins = (
        await db.execute(
            select(UserLoginLog, User.username)
            .join(User, User.id == UserLoginLog.user_id)
            .order_by(UserLoginLog.login_at.desc())
            .limit(8)
        )
    ).all()

    return {
        "generated_at": now.isoformat(),
        "system": {
            "admin_api_online": True,
            "stockai_api_online": internal is not None,
            "scheduler_running": bool(scheduler.get("running")),
            "scheduler_phase": scheduler.get("current_phase"),
            "active_hires": scheduler.get("active_hires", 0),
            "engine_active_sessions": engine_active,
        },
        "ops": {
            "total_users": total_users,
            "new_users_today": new_users_today,
            "total_agents": total_agents,
            "hire_active": hire_active,
            "signal_today": signal_today,
            "trade_today": trade_row[0],
            "trade_amount_today": float(trade_row[1] or 0),
            "pnl_today": round(float(pnl_row[0] or 0), 2),
            "feedback_pending": feedback_pending,
        },
        "todos": todos,
        "recent": {
            "signals": [
                {
                    "id": s.id,
                    "signal_id": s.signal_id,
                    "action": s.action,
                    "symbol": s.symbol,
                    "symbol_name": s.symbol_name,
                    "status": s.status,
                    "user_id": s.user_id,
                    "created_at": _f(s.created_at),
                }
                for s in recent_signals
            ],
            "orders": [
                {
                    "id": o.id,
                    "user_id": o.user_id,
                    "symbol": o.symbol,
                    "name": o.name,
                    "side": o.side,
                    "price": float(o.price),
                    "quantity": o.quantity,
                    "status": o.status,
                    "created_at": _f(o.created_at),
                }
                for o in recent_orders
            ],
            "logins": [
                {
                    "user_id": ll.user_id,
                    "username": username,
                    "login_at": _f(ll.login_at),
                    "ip": ll.ip,
                    "platform": ll.platform,
                }
                for ll, username in recent_logins
            ],
        },
    }
