"""
app/api/v1/admin/agents.py — Agent 交易员监控（只读）

能力：
  GET  /overview       总览 KPI（交易员/雇佣/托管引擎/今日信号/成交/盈亏/调度器）
  GET  /list           交易员列表（含雇佣数、最新表现）
  GET  /engine         托管引擎实时状态（跨进程拉 C 端 8000 internal 接口）
  GET  /sessions       用户雇佣会话明细（分页/状态筛选）
  GET  /{agent_id}     单个交易员详情 + 雇佣用户

数据源：agent.agent_traders / agent.user_agents / agent.agent_performances
       + signals / trades / orders 当日聚合 + HostedEngine 运行时快照
"""
import os
from datetime import date, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin, require_permission
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.agent import AgentPerformance, AgentTrader, UserAgent
from app.models.signals import Signal
from app.models.trading import Trade
from app.models.user import User

router = APIRouter()

PERM_VIEW = "agents:view"
PERM_MANAGE = "agents:manage"

INTERNAL_BASE = os.getenv("ADMIN_INTERNAL_BASE", "http://127.0.0.1:8000")
INTERNAL_TOKEN = os.getenv("ADMIN_INTERNAL_TOKEN", "stockai_admin_internal_2026")

_SESSION_TTL = timedelta(seconds=5)


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


async def _fetch_internal_overview():
    """跨进程拉 C 端 HostedEngine + 调度器状态（带 5s 缓存）"""
    async with httpx.AsyncClient(timeout=3.0) as client:
        resp = await client.get(
            f"{INTERNAL_BASE}/api/v1/internal/hosted/overview",
            headers={"X-Internal-Token": INTERNAL_TOKEN},
        )
        resp.raise_for_status()
        return resp.json()


@router.get("/overview")
async def agents_overview(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM_VIEW)),
):
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    week_ago = (today - timedelta(days=6)).isoformat()

    # 交易员市场
    agent_total = (
        await db.execute(select(func.count(AgentTrader.id)))
    ).scalar() or 0
    agent_active = (
        await db.execute(
            select(func.count(AgentTrader.id)).where(AgentTrader.is_active.is_(True))
        )
    ).scalar() or 0

    # 雇佣关系
    hire_total = (
        await db.execute(select(func.count(UserAgent.id)))
    ).scalar() or 0
    hire_active = (
        await db.execute(
            select(func.count(UserAgent.id)).where(UserAgent.status == "active")
        )
    ).scalar() or 0
    hire_capital = (
        await db.execute(
            select(func.coalesce(func.sum(UserAgent.allocated_capital), 0)).where(
                UserAgent.status == "active"
            )
        )
    ).scalar() or 0

    # 今日信号 / 成交 / 盈亏
    signal_today = (
        await db.execute(
            select(func.count(Signal.id)).where(Signal.created_at >= today_start)
        )
    ).scalar() or 0
    signal_exec = (
        await db.execute(
            select(func.count(Signal.id)).where(
                Signal.created_at >= today_start, Signal.status == "EXECUTED"
            )
        )
    ).scalar() or 0
    trade_today = (
        await db.execute(
            select(
                func.count(Trade.id),
                func.coalesce(func.sum(Trade.amount), 0),
                func.coalesce(func.sum(Trade.commission + Trade.tax), 0),
            ).where(Trade.trade_date == today)
        )
    ).one()
    pnl_today_row = (
        await db.execute(
            select(
                func.coalesce(
                    func.sum(case((Trade.side == "BUY", Trade.amount * -1), else_=Trade.amount)),
                    0,
                )
            ).where(Trade.trade_date == today)
        )
    ).one()

    # 引擎实时状态（失败不阻塞整体）
    engine = None
    try:
        engine = await _fetch_internal_overview()
    except Exception:
        engine = {"error": "engine_unreachable", "active_count": 0, "total_sessions": 0, "scheduler": {}}

    return {
        "agent_total": agent_total,
        "agent_active": agent_active,
        "hire_total": hire_total,
        "hire_active": hire_active,
        "hire_capital": float(hire_capital or 0),
        "signal_today": signal_today,
        "signal_executed_today": signal_exec,
        "trade_today": trade_today[0],
        "trade_amount_today": float(trade_today[1] or 0),
        "trade_fee_today": float(trade_today[2] or 0),
        "pnl_today": round(float(pnl_today_row[0] or 0), 2),
        "engine_active_sessions": (engine or {}).get("active_count", 0),
        "engine_total_sessions": (engine or {}).get("total_sessions", 0),
        "scheduler_phase": ((engine or {}).get("scheduler") or {}).get("current_phase"),
        "engine_error": (engine or {}).get("error"),
    }


@router.get("/list")
async def agents_list(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM_VIEW)),
    keyword: str = Query("", description="按 code_name/tag 模糊"),
    active_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    conds = []
    if keyword:
        conds.append(
            (AgentTrader.code_name.ilike(f"%{keyword}%"))
            | (AgentTrader.tag.ilike(f"%{keyword}%"))
        )
    if active_only:
        conds.append(AgentTrader.is_active.is_(True))

    total = (
        await db.execute(select(func.count(AgentTrader.id)).where(*conds))
    ).scalar() or 0

    rows = (
        await db.execute(
            select(AgentTrader)
            .where(*conds)
            .order_by(AgentTrader.sort_order, AgentTrader.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    agent_ids = [r.id for r in rows]
    hire_map = {}
    perf_map = {}
    if agent_ids:
        hire_rows = (
            await db.execute(
                select(
                    UserAgent.agent_id,
                    func.count(UserAgent.id).label("hire_count"),
                    func.sum(case((UserAgent.status == "active", 1), else_=0)).label("active_count"),
                )
                .where(UserAgent.agent_id.in_(agent_ids))
                .group_by(UserAgent.agent_id)
            )
        ).all()
        hire_map = {h.agent_id: h for h in hire_rows}

        perf_rows = (
            await db.execute(
                select(AgentPerformance)
                .where(AgentPerformance.agent_id.in_(agent_ids))
                .order_by(AgentPerformance.agent_id, AgentPerformance.period_end.desc())
            )
        ).scalars().all()
        for p in perf_rows:
            if p.agent_id not in perf_map:
                perf_map[p.agent_id] = p

    items = []
    for r in rows:
        h = hire_map.get(r.id)
        p = perf_map.get(r.id)
        items.append({
            "id": r.id,
            "code_name": r.code_name,
            "tag": r.tag,
            "avatar_url": r.avatar_url,
            "description": r.description,
            "masters": r.masters,
            "hire_price_points": r.hire_price_points,
            "profit_share_pct": float(r.profit_share_pct or 0),
            "is_active": r.is_active,
            "sort_order": r.sort_order,
            "annual_return": float(r.annual_return) if r.annual_return is not None else None,
            "max_drawdown": float(r.max_drawdown) if r.max_drawdown is not None else None,
            "sharpe_ratio": float(r.sharpe_ratio) if r.sharpe_ratio is not None else None,
            "win_rate": float(r.win_rate) if r.win_rate is not None else None,
            "total_trades": r.total_trades,
            "hire_count": int(h.hire_count) if h else 0,
            "active_hire_count": int(h.active_count or 0) if h else 0,
            "latest_period": p.period if p else None,
            "latest_period_end": p.period_end.isoformat() if p and p.period_end else None,
            "latest_return_pct": float(p.return_pct) if p else None,
            "created_at": _f(r.created_at),
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/engine")
async def agents_engine(
    _: AdminUser = Depends(require_permission(PERM_VIEW)),
):
    try:
        data = await _fetch_internal_overview()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"引擎状态拉取失败: {e}")
    return data


@router.get("/sessions")
async def agents_sessions(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM_MANAGE)),
    status: str = Query("", description="active/expired/stopped 空=全部"),
    keyword: str = Query("", description="用户名/交易员名模糊"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    conds = []
    if status:
        conds.append(UserAgent.status == status)
    if keyword:
        conds.append(
            (User.username.ilike(f"%{keyword}%"))
            | (AgentTrader.code_name.ilike(f"%{keyword}%"))
        )

    base = (
        select(UserAgent, User, AgentTrader)
        .join(User, User.id == UserAgent.user_id)
        .join(AgentTrader, AgentTrader.id == UserAgent.agent_id)
        .where(*conds)
    )
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar() or 0
    rows = (
        await db.execute(
            base.order_by(UserAgent.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items = []
    for ua, user, trader in rows:
        items.append({
            "id": ua.id,
            "user_id": ua.user_id,
            "username": user.username,
            "agent_id": ua.agent_id,
            "code_name": trader.code_name,
            "tag": trader.tag,
            "status": ua.status,
            "management_mode": ua.management_mode,
            "allocated_capital": float(ua.allocated_capital) if ua.allocated_capital is not None else None,
            "current_pnl": float(ua.current_pnl) if ua.current_pnl is not None else None,
            "hired_at": _f(ua.hired_at),
            "expires_at": _f(ua.expires_at),
            "updated_at": _f(ua.updated_at),
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{agent_id}")
async def agents_detail(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM_VIEW)),
):
    trader = (
        await db.execute(select(AgentTrader).where(AgentTrader.id == agent_id))
    ).scalar_one_or_none()
    if trader is None:
        raise HTTPException(status_code=404, detail="交易员不存在")

    hires = (
        await db.execute(
            select(UserAgent, User)
            .join(User, User.id == UserAgent.user_id)
            .where(UserAgent.agent_id == agent_id)
            .order_by(UserAgent.updated_at.desc())
            .limit(50)
        )
    ).all()

    perfs = (
        await db.execute(
            select(AgentPerformance)
            .where(AgentPerformance.agent_id == agent_id)
            .order_by(AgentPerformance.period_end.desc())
            .limit(12)
        )
    ).scalars().all()

    return {
        "trader": {
            "id": trader.id,
            "code_name": trader.code_name,
            "tag": trader.tag,
            "avatar_url": trader.avatar_url,
            "description": trader.description,
            "strategy_detail": trader.strategy_detail,
            "masters": trader.masters,
            "hire_price_points": trader.hire_price_points,
            "profit_share_pct": float(trader.profit_share_pct or 0),
            "is_active": trader.is_active,
            "annual_return": float(trader.annual_return) if trader.annual_return is not None else None,
            "max_drawdown": float(trader.max_drawdown) if trader.max_drawdown is not None else None,
            "sharpe_ratio": float(trader.sharpe_ratio) if trader.sharpe_ratio is not None else None,
            "win_rate": float(trader.win_rate) if trader.win_rate is not None else None,
            "total_trades": trader.total_trades,
            "radar_scores": trader.radar_scores,
            "salary_curve": trader.salary_curve,
            "created_at": _f(trader.created_at),
        },
        "hires": [
            {
                "id": ua.id,
                "user_id": ua.user_id,
                "username": user.username,
                "status": ua.status,
                "management_mode": ua.management_mode,
                "allocated_capital": float(ua.allocated_capital) if ua.allocated_capital is not None else None,
                "current_pnl": float(ua.current_pnl) if ua.current_pnl is not None else None,
                "hired_at": _f(ua.hired_at),
                "expires_at": _f(ua.expires_at),
            }
            for ua, user in hires
        ],
        "performances": [
            {
                "period": p.period,
                "period_end": p.period_end.isoformat() if p.period_end else None,
                "return_pct": float(p.return_pct),
                "benchmark_return_pct": float(p.benchmark_return_pct) if p.benchmark_return_pct is not None else None,
                "alpha": float(p.alpha) if p.alpha is not None else None,
                "max_drawdown": float(p.max_drawdown) if p.max_drawdown is not None else None,
                "sharpe_ratio": float(p.sharpe_ratio) if p.sharpe_ratio is not None else None,
                "win_rate": float(p.win_rate) if p.win_rate is not None else None,
            }
            for p in perfs
        ],
    }
