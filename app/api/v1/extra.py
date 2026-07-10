"""
app/api/v1/extra.py — 扩展端点（通知 / 信号 / 指标 / 事件）

补齐前端已建页面但后端缺失的接口，消除 404：
- GET /notifications       通知列表（分页 + 未读数）
- PUT /notifications/{id}/read  标记单条已读
- PUT /notifications/read-all   全部已读
- DELETE /notifications/{id}    删除单条
- DELETE /notifications         清空全部
- GET /signals              最近 AI 信号（实时跑委员会，5 分钟缓存）
- GET /metrics              用户指标看板
- GET /events               用户事件流
"""
import time
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()

# ── 信号缓存（避免每次刷新都跑 LLM 委员会）──
_signal_cache: dict = {"ts": 0.0, "data": []}
_SIGNAL_TTL = 300  # 5 分钟


# ══════════════════════════════════════════════════════════════════════════
#  通知中心 (Notifications CRUD)
# ══════════════════════════════════════════════════════════════════════════

@router.get("/notifications")
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """通知列表（分页 + 未读计数）"""
    # 总数
    total_row = await db.execute(
        text("SELECT count(*) FROM public.notifications WHERE user_id = :uid"),
        {"uid": user.id},
    )
    total = total_row.scalar()

    # 未读数
    unread_row = await db.execute(
        text("SELECT count(*) FROM public.notifications WHERE user_id = :uid AND read = false"),
        {"uid": user.id},
    )
    unread_count = unread_row.scalar()

    # 分页列表
    rows = await db.execute(
        text(
            "SELECT id, type, title, content, read, data, created_at "
            "FROM public.notifications WHERE user_id = :uid "
            "ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ),
        {"uid": user.id, "limit": limit, "offset": offset},
    )
    items = [
        {
            "id": str(r[0]),
            "type": r[1],
            "title": r[2],
            "content": r[3] or "",
            "read": r[4],
            "data": r[5] or {},
            "created_at": r[6].isoformat() if r[6] else None,
        }
        for r in rows.fetchall()
    ]

    return {
        "items": items,
        "total": total,
        "unread_count": unread_count,
        "limit": limit,
        "offset": offset,
    }


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """标记单条已读"""
    result = await db.execute(
        text(
            "UPDATE public.notifications SET read = true "
            "WHERE id = :id AND user_id = :uid"
        ),
        {"id": notification_id, "uid": user.id},
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="通知不存在")
    return {"success": True}


@router.put("/notifications/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """全部标记已读"""
    await db.execute(
        text(
            "UPDATE public.notifications SET read = true "
            "WHERE user_id = :uid AND read = false"
        ),
        {"uid": user.id},
    )
    await db.commit()
    return {"success": True}


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除单条通知"""
    result = await db.execute(
        text(
            "DELETE FROM public.notifications WHERE id = :id AND user_id = :uid"
        ),
        {"id": notification_id, "uid": user.id},
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="通知不存在")
    return {"success": True}


@router.delete("/notifications")
async def clear_all_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """清空全部通知"""
    await db.execute(
        text("DELETE FROM public.notifications WHERE user_id = :uid"),
        {"uid": user.id},
    )
    await db.commit()
    return {"success": True}


# ══════════════════════════════════════════════════════════════════════════
#  AI 信号 / 指标 / 事件
# ══════════════════════════════════════════════════════════════════════════

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


@router.post("/metrics")
async def post_metrics(
    payload: dict,
    user: User = Depends(get_current_user),
):
    """接收前端性能监控批量上报（perf-monitor.ts），当前仅记录数量"""
    metrics = payload.get("metrics", [])
    return {"success": True, "received": len(metrics)}


@router.post("/events")
async def post_events(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """接收前端埋点批量上报（tracker.ts），当前仅记录日志"""
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

# ══════════════════════════════════════════════════════════════════════════
#  用户反馈
# ══════════════════════════════════════════════════════════════════════════

@router.post("/feedback")
async def submit_feedback(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """提交用户反馈"""
    fb_type = payload.get("type", "other")
    description = payload.get("description", "").strip()
    contact = payload.get("contact", "").strip() or None

    if not description:
        raise HTTPException(status_code=400, detail="反馈内容不能为空")

    await db.execute(
        text(
            "INSERT INTO public.feedbacks (user_id, type, description, contact) "
            "VALUES (:uid, :type, :desc, :contact)"
        ),
        {"uid": user.id, "type": fb_type, "desc": description, "contact": contact},
    )
    await db.commit()

    return {"success": True, "message": "反馈已提交，感谢您的建议！"}


