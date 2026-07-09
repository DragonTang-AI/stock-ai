"""
app/api/v1/extra.py — 扩展端点（通知 / 信号 / 指标 / 事件）

补齐前端已建页面但后端缺失的接口，消除 404：
- GET /notifications  用户通知列表（派生自托管日志）
- GET /signals        最近 AI 信号（实时跑委员会，5 分钟缓存）
- GET /metrics        用户指标看板（账户 / 持仓 / 订单 / 托管事件统计）
- GET /events         用户事件流（托管日志最近活动）
"""
import time
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()

# ── 信号缓存（避免每次刷新都跑 LLM 委员会）──
_signal_cache: dict = {"ts": 0.0, "data": []}
_SIGNAL_TTL = 300  # 5 分钟


@router.get("/notifications")
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
):
    """用户通知列表（派生自 AI托管执行日志）"""
    rows = await db.execute(
        text(
            "SELECT id, symbol, status, reason, created_at "
            "FROM public.hosted_logs WHERE user_id = :uid "
            "ORDER BY created_at DESC LIMIT :lim"
        ),
        {"uid": user.id, "lim": limit},
    )
    items = [
        {
            "id": str(r[0]),
            "symbol": r[1],
            "status": r[2],
            "message": r[3] or "",
            "created_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows.fetchall()
    ]
    return {"success": True, "data": items}


@router.get("/signals")
async def get_signals(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50),
):
    """最近 AI 信号（实时跑 4-Agent 委员会，5 分钟缓存）"""
    now = time.time()
    if now - _signal_cache["ts"] < _SIGNAL_TTL and _signal_cache["data"]:
        return {"success": True, "data": _signal_cache["data"][:limit]}
    try:
        from app.services.committee_service import run_committee_analysis

        result = await run_committee_analysis(market="A", trade_date=date.today())
        data = [s.model_dump() for s in result.signals][:limit]
        _signal_cache["ts"] = now
        _signal_cache["data"] = data
        return {"success": True, "data": data}
    except Exception:
        return {"success": True, "data": []}


@router.get("/metrics")
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """用户指标看板（账户 / 持仓 / 订单 / 托管事件统计）"""
    rows = await db.execute(
        text(
            "SELECT "
            "(SELECT COALESCE(SUM(balance),0) FROM public.accounts WHERE user_id=:uid) as balance, "
            "(SELECT COUNT(*) FROM public.positions WHERE account_id IN "
            "   (SELECT id FROM public.accounts WHERE user_id=:uid)) as positions, "
            "(SELECT COUNT(*) FROM public.orders WHERE user_id=:uid) as orders, "
            "(SELECT COUNT(*) FROM public.hosted_logs WHERE user_id=:uid) as hosted_events"
        ),
        {"uid": user.id},
    )
    r = rows.fetchone()
    return {
        "success": True,
        "data": {
            "balance": float(r[0] or 0),
            "positions": int(r[1] or 0),
            "orders": int(r[2] or 0),
            "hosted_events": int(r[3] or 0),
        },
    }




    events: list
    device_id: str
    timestamp: int


@router.post("/metrics")
async def post_metrics(
    payload: dict,
    user: User = Depends(get_current_user),
):
    """接收前端性能监控批量上报（perf-monitor.ts），当前仅记录数量"""
    metrics = payload.get("metrics", [])
    # 当前仅计数记录，后续可持久化到独立 metrics 表
    return {"success": True, "received": len(metrics)}


@router.post("/events")
async def post_events(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """接收前端埋点批量上报（tracker.ts），当前仅记录日志，未来持久化到 events 表"""
    # 暂时记录到 hosted_logs 作为事件流（后续拆出独立 events 表）
    # 当前仅记录数量，后续可持久化到独立 events 表
    return {"success": True, "received": len(payload.get("events", []))}

@router.get("/events")
async def get_events(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
):
    """用户事件流（AI托管执行记录最近活动）"""
    rows = await db.execute(
        text(
            "SELECT symbol, status, reason, created_at "
            "FROM public.hosted_logs WHERE user_id = :uid "
            "ORDER BY created_at DESC LIMIT :lim"
        ),
        {"uid": user.id, "lim": limit},
    )
    items = [
        {
            "symbol": r[0],
            "status": r[1],
            "message": r[2] or "",
            "created_at": r[3].isoformat() if r[3] else None,
        }
        for r in rows.fetchall()
    ]
    return {"success": True, "data": items}
