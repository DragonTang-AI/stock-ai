"""
app/api/v1/admin/backtest.py — 回测追踪查询（只读）
提供：推荐记录列表、胜率与收益统计、图表数据（累计收益/超额对比）。
仅做只读查询，不触发任何回测/生成任务。
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin, require_permission
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.pick_tracking import PickTracking

router = APIRouter()


def _f(v) -> float | None:
    """Decimal → float 序列化"""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    return v


def _row_to_dict(rec: PickTracking) -> dict:
    return {
        "id": rec.id,
        "trade_date": rec.trade_date,
        "market": rec.market,
        "engine": rec.engine,
        "symbol": rec.symbol,
        "symbol_name": rec.symbol_name,
        "action": rec.action,
        "confidence": rec.confidence,
        "entry_price": _f(rec.entry_price),
        "t5_return": _f(rec.t5_return),
        "t5_benchmark_return": _f(rec.t5_benchmark_return),
        "t20_return": _f(rec.t20_return),
        "t20_benchmark_return": _f(rec.t20_benchmark_return),
        "backtest_updated_at": rec.backtest_updated_at.isoformat() if rec.backtest_updated_at else None,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


@router.get("/picks")
async def list_picks(
    trade_date: str | None = Query(default=None, description="推荐日期 YYYY-MM-DD"),
    market: str | None = Query(default=None, description="A/HK"),
    engine: str | None = Query(default=None, description="factor/committee_llm"),
    symbol: str | None = Query(default=None, description="股票代码模糊匹配"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission("backtest:view")),
):
    """推荐记录列表（按条件筛选 + 分页）"""
    conds = []
    if trade_date:
        conds.append(PickTracking.trade_date == trade_date)
    if market:
        conds.append(PickTracking.market == market)
    if engine:
        conds.append(PickTracking.engine == engine)
    if symbol:
        conds.append(PickTracking.symbol.ilike(f"%{symbol}%"))

    total = await db.scalar(
        select(func.count(PickTracking.id)).where(*conds)
    ) or 0

    result = await db.execute(
        select(PickTracking)
        .where(*conds)
        .order_by(PickTracking.trade_date.desc(), PickTracking.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_row_to_dict(r) for r in result.scalars().all()]

    return {"code": 0, "data": {"items": items, "total": total, "page": page, "page_size": page_size}, "message": "ok"}


@router.get("/stats")
async def backtest_stats(
    engine: str | None = Query(default=None, description="不传则对比全部引擎"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission("backtest:view")),
):
    """胜率与收益统计（按引擎分组）"""
    conds = []
    if engine:
        conds.append(PickTracking.engine == engine)

    result = await db.execute(
        select(
            PickTracking.engine,
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
        .where(*conds)
        .group_by(PickTracking.engine)
    )
    engines = []
    for row in result.all():
        _, total, t5_done, t20_done, t5_win, t20_win, t5_avg, t20_avg, t5_bm, t20_bm = row
        engines.append({
            "engine": row[0],
            "total": int(total or 0),
            "t5_done": int(t5_done or 0),
            "t20_done": int(t20_done or 0),
            "t5_win_rate": round(float(t5_win or 0) / float(t5_done or 1) * 100, 2) if t5_done else None,
            "t20_win_rate": round(float(t20_win or 0) / float(t20_done or 1) * 100, 2) if t20_done else None,
            "t5_avg_return": _f(t5_avg),
            "t20_avg_return": _f(t20_avg),
            "t5_avg_excess": round(_f(t5_avg) - _f(t5_bm), 4) if t5_avg is not None and t5_bm is not None else None,
            "t20_avg_excess": round(_f(t20_avg) - _f(t20_bm), 4) if t20_avg is not None and t20_bm is not None else None,
        })
    return {"code": 0, "data": {"engines": engines}, "message": "ok"}


@router.get("/chart")
async def backtest_chart(
    engine: str | None = Query(default=None, description="不传则全部"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission("backtest:view")),
):
    """图表数据：按交易日聚合平均收益与超额（累计曲线用）"""
    conds = []
    if engine:
        conds.append(PickTracking.engine == engine)

    result = await db.execute(
        select(
            PickTracking.trade_date,
            PickTracking.engine,
            func.avg(PickTracking.t5_return),
            func.avg(PickTracking.t20_return),
            func.avg(PickTracking.t5_benchmark_return),
            func.avg(PickTracking.t20_benchmark_return),
        )
        .where(*conds)
        .group_by(PickTracking.trade_date, PickTracking.engine)
        .order_by(PickTracking.trade_date)
    )
    by_date = {}
    for row in result.all():
        d, eng, t5, t20, t5b, t20b = row
        by_date.setdefault(d, {})[eng] = {
            "t5_avg": _f(t5),
            "t20_avg": _f(t20),
            "t5_excess": round(_f(t5) - _f(t5b), 4) if t5 is not None and t5b is not None else None,
            "t20_excess": round(_f(t20) - _f(t20b), 4) if t20 is not None and t20b is not None else None,
        }
    return {
        "code": 0,
        "data": {
            "dates": sorted(by_date.keys()),
            "points": by_date,
        },
        "message": "ok",
    }
