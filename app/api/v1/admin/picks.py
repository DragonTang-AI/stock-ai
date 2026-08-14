"""
app/api/v1/admin/picks.py — 每日推荐管理（M3）
提供：双引擎推荐查看（factor / committee_llm）、引擎状态、手动刷新生成。
写操作（refresh）需要 picks:refresh 权限并记录操作日志。
"""
import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin, require_permission
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.daily_pick import DailyPick
from app.models.operation_log import OperationLog
from app.services.daily_picks_service import refresh_daily_picks, SUPPORTED_ENGINES

router = APIRouter()

ENGINES = ["factor", "committee_llm"]


def _pick_row_to_dict(rec: DailyPick) -> dict:
    return {
        "id": rec.id,
        "trade_date": rec.trade_date,
        "market": rec.market,
        "engine": rec.engine,
        "source": rec.source,
        "status": rec.status,
        "error_msg": rec.error_msg,
        "generated_at": rec.updated_at.isoformat() if rec.updated_at else None,
        "pick_count": len(json.loads(rec.picks_json or "[]")),
        "picks": json.loads(rec.picks_json or "[]"),
    }


async def _log(db: AsyncSession, admin: AdminUser, module: str, action: str, detail: str = "") -> None:
    db.add(
        OperationLog(
            user_id=admin.id,
            username=admin.username,
            module=module,
            action=action,
            detail=detail[:500],
            ip="",
        )
    )


@router.get("/list")
async def list_daily_picks(
    trade_date: str | None = Query(default=None, description="推荐日期 YYYY-MM-DD，默认今日"),
    market: str = Query(default="A", description="A/HK"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission("picks:view")),
):
    """双引擎每日推荐查看（factor + committee_llm）"""
    td = trade_date or date.today().isoformat()

    result = await db.execute(
        select(DailyPick)
        .where(DailyPick.trade_date == td, DailyPick.market == market)
        .order_by(DailyPick.engine)
    )
    rows = result.scalars().all()

    engines = {}
    for rec in rows:
        info = _pick_row_to_dict(rec)
        engines[rec.engine] = {
            "status": rec.status,
            "source": rec.source,
            "error_msg": rec.error_msg,
            "generated_at": rec.updated_at.isoformat() if rec.updated_at else None,
            "pick_count": info["pick_count"],
            "picks": info["picks"],
        }

    return {
        "code": 0,
        "data": {
            "trade_date": td,
            "market": market,
            "engines": engines,
            "supported_engines": ENGINES,
        },
        "message": "ok",
    }


@router.post("/refresh")
async def refresh_picks(
    engine: str = Query(default="committee_llm", description="factor/committee_llm"),
    market: str = Query(default="A", description="A/HK"),
    top_n: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("picks:refresh")),
):
    """手动刷新：强制重新生成当日推荐（走现有 service 层，不侵入引擎算法）"""
    if engine not in SUPPORTED_ENGINES:
        raise HTTPException(status_code=400, detail=f"不支持的引擎: {engine}")

    result = await refresh_daily_picks(market=market, top_n=top_n, engine=engine)

    await _log(
        db, admin, "picks", "refresh",
        f"手动刷新每日推荐 engine={engine} market={market} top_n={top_n} "
        f"success={result.get('success')} picks={len(result.get('picks') or [])}",
    )
    await db.commit()

    if not result.get("success"):
        return {"code": 1, "data": result, "message": result.get("error") or result.get("message") or "刷新失败"}
    return {"code": 0, "data": result, "message": "ok"}
