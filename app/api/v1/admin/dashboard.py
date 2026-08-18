"""
app/api/v1/admin/dashboard.py — 首页大屏看板聚合接口（只读）
提供：KPI 汇总、今日双引擎推荐、回测累计曲线、最近信号/订单/持仓、调度状态。
一次请求拉全首页大屏所需数据，仅供 Dashboard 使用。
"""
import json
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin, require_permission
from app.core.database import get_db
from app.engine.scheduler_v2 import get_status
from app.models.admin_user import AdminUser
from app.models.daily_pick import DailyPick
from app.models.pick_tracking import PickTracking
from app.models.signals import Signal
from app.models.trading import Account, Order, Position, Trade

router = APIRouter()

PERM = "dashboard:view"


def _f(v):
    if v is None:
        return None
    from decimal import Decimal
    if isinstance(v, Decimal):
        return float(v)
    return v


@router.get("/summary")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM)),
):
    today = date.today().isoformat()

    # ── KPI：今日推荐 ──
    picks_rows = (
        await db.execute(
            select(DailyPick).where(DailyPick.trade_date == today).order_by(DailyPick.engine)
        )
    ).scalars().all()
    today_picks = {}
    for rec in picks_rows:
        try:
            picks = json.loads(rec.picks_json or "[]")
        except Exception:
            picks = []
        today_picks[rec.engine] = {
            "status": rec.status,
            "source": rec.source,
            "generated_at": rec.updated_at.isoformat() if rec.updated_at else None,
            "pick_count": len(picks),
            "error_msg": rec.error_msg,
            "picks": picks[:8],
        }

    # ── KPI：回测胜率/超额（全部引擎合并） ──
    row = (
        await db.execute(
            select(
                func.count(PickTracking.id),
                func.sum(case((PickTracking.t5_return.isnot(None), 1), else_=0)),
                func.sum(case((PickTracking.t20_return.isnot(None), 1), else_=0)),
                func.sum(case((PickTracking.t5_return > 0, 1), else_=0)),
                func.sum(case((PickTracking.t20_return > 0, 1), else_=0)),
                func.avg(PickTracking.t5_return),
                func.avg(PickTracking.t20_return),
                func.avg(PickTracking.t5_benchmark_return),
                func.avg(PickTracking.t20_benchmark_return),
            )
        )
    ).one()
    total, t5_done, t20_done, t5_win, t20_win, t5_avg, t20_avg, t5_bm, t20_bm = row

    # ── 回测曲线：按交易日聚合（双引擎平均） ──
    chart_rows = (
        await db.execute(
            select(
                PickTracking.trade_date,
                func.avg(PickTracking.t5_return),
                func.avg(PickTracking.t20_return),
                func.avg(PickTracking.t5_benchmark_return),
                func.avg(PickTracking.t20_benchmark_return),
            )
            .group_by(PickTracking.trade_date)
            .order_by(PickTracking.trade_date)
        )
    ).all()
    chart = [
        {
            "trade_date": r[0],
            "t5_avg": _f(r[1]),
            "t20_avg": _f(r[2]),
            "t5_bm": _f(r[3]),
            "t20_bm": _f(r[4]),
        }
        for r in chart_rows
    ]

    # ── 最近信号 ──
    sig_rows = (
        await db.execute(select(Signal).order_by(desc(Signal.created_at)).limit(8))
    ).scalars().all()
    signals = [
        {
            "symbol": s.symbol,
            "symbol_name": s.symbol_name,
            "action": s.action,
            "confidence": s.confidence,
            "status": s.status,
            "reason": (s.reason or "")[:80],
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sig_rows
    ]

    # ── 最近订单 ──
    order_rows = (
        await db.execute(select(Order).order_by(desc(Order.created_at)).limit(8))
    ).scalars().all()
    orders = [
        {
            "symbol": o.symbol,
            "name": o.name,
            "side": o.side,
            "price": _f(o.price),
            "quantity": o.quantity,
            "amount": _f(o.amount),
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in order_rows
    ]

    # ── 持仓 TOP（按市值） ──
    pos_rows = (
        await db.execute(select(Position).order_by(desc(Position.market_value)).limit(8))
    ).scalars().all()
    positions = [
        {
            "symbol": p.symbol,
            "name": p.name,
            "quantity": p.quantity,
            "cost_price": _f(p.cost_price),
            "market_price": _f(p.market_price),
            "market_value": _f(p.market_value),
            "profit_pct": _f(p.profit_pct),
        }
        for p in pos_rows
    ]

    # ── 账户/交易汇总 ──
    acc_rows = (await db.execute(select(Account))).scalars().all()
    total_balance = sum(_f(a.balance) or 0 for a in acc_rows)
    total_frozen = sum(_f(a.frozen) or 0 for a in acc_rows)
    total_mv = sum(_f(p.market_value) or 0 for p in pos_rows)
    trade_cnt = await db.scalar(select(func.count(Trade.id)))

    return {
        "code": 0,
        "data": {
            "trade_date": today,
            "kpi": {
                "today_pick_count": sum(v.get("pick_count", 0) for v in today_picks.values()),
                "track_total": int(total or 0),
                "t5_win_rate": round(float(t5_win or 0) / float(t5_done or 1) * 100, 2) if t5_done else None,
                "t20_win_rate": round(float(t20_win or 0) / float(t20_done or 1) * 100, 2) if t20_done else None,
                "t5_avg_return": _f(t5_avg),
                "t20_avg_return": _f(t20_avg),
                "t5_avg_excess": round(_f(t5_avg) - _f(t5_bm), 2) if t5_avg is not None and t5_bm is not None else None,
                "t20_avg_excess": round(_f(t20_avg) - _f(t20_bm), 2) if t20_avg is not None and t20_bm is not None else None,
                "position_count": len(pos_rows),
                "total_assets": round(total_balance + total_mv, 2),
                "total_balance": round(total_balance, 2),
                "total_frozen": round(total_frozen, 2),
                "total_trades": int(trade_cnt or 0),
            },
            "today_picks": today_picks,
            "chart": chart,
            "signals": signals,
            "orders": orders,
            "positions": positions,
            "scheduler": get_status(),
        },
        "message": "ok",
    }
