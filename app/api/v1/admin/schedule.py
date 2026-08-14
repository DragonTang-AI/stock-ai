"""
app/api/v1/admin/schedule.py — 调度监控（M3）
提供：调度器状态、任务列表与最近执行情况、手动触发补跑（推荐/回测）。
写操作（trigger）需要 schedule:trigger 权限并记录操作日志。
"""
import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin, require_permission
from app.core.database import get_db
from app.engine.scheduler_v2 import get_status
from app.models.admin_user import AdminUser
from app.models.daily_pick import DailyPick
from app.models.operation_log import OperationLog
from app.models.pick_tracking import PickTracking
from app.services.daily_backtest_service import run_daily_backtest
from app.services.daily_picks_service import refresh_daily_picks

router = APIRouter()

TASKS = [
    {
        "key": "daily_picks",
        "name": "每日推荐生成",
        "schedule": "每天 08:00-08:30",
        "desc": "双引擎（factor + committee_llm）预生成当日推荐",
        "action": "refresh",
    },
    {
        "key": "daily_backtest",
        "name": "每日回测",
        "schedule": "每天 16:30-17:00",
        "desc": "对到期推荐票回填 T+5/T+20 收益与基准超额",
        "action": "trigger",
    },
    {
        "key": "trade_cycle",
        "name": "交易调度周期",
        "schedule": "每 5 分钟",
        "desc": "活跃雇佣关系信号处理（交易时段内执行）",
        "action": "none",
    },
]


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


@router.get("/status")
async def scheduler_status(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission("schedule:view")),
):
    """调度器运行状态 + 最近执行记录"""
    status = get_status()
    today = date.today().isoformat()

    # 今日各引擎推荐生成状态
    picks_result = await db.execute(
        select(DailyPick)
        .where(DailyPick.trade_date == today)
        .order_by(DailyPick.engine)
    )
    picks_rows = picks_result.scalars().all()
    daily_picks_status = {
        r.engine: {
            "status": r.status,
            "source": r.source,
            "generated_at": r.updated_at.isoformat() if r.updated_at else None,
            "pick_count": len(json.loads(r.picks_json or "[]")),
            "error_msg": r.error_msg,
        }
        for r in picks_rows
    }

    # 最近一次回测记录
    last_backtest = await db.scalar(
        select(func.max(PickTracking.backtest_updated_at))
    )

    return {
        "code": 0,
        "data": {
            "scheduler": status,
            "daily_picks": daily_picks_status,
            "last_backtest_at": last_backtest.isoformat() if last_backtest else None,
            "trade_date": today,
        },
        "message": "ok",
    }


@router.get("/tasks")
async def scheduler_tasks(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission("schedule:view")),
):
    """任务列表 + 最近执行情况"""
    status = get_status()
    today = date.today().isoformat()

    items = []
    for t in TASKS:
        last_run = None
        detail = ""
        if t["key"] == "daily_picks":
            rec = await db.execute(
                select(DailyPick)
                .where(DailyPick.trade_date == today)
                .order_by(DailyPick.updated_at.desc())
                .limit(1)
            )
            row = rec.scalar_one_or_none()
            if row:
                last_run = row.updated_at.isoformat() if row.updated_at else None
                detail = f"engine={row.engine} status={row.status} picks={len(json.loads(row.picks_json or '[]'))}"
        elif t["key"] == "daily_backtest":
            last_run = await db.scalar(
                select(func.max(PickTracking.backtest_updated_at))
            )
            if last_run:
                detail = "最近回测已完成"
                last_run = last_run.isoformat()
        elif t["key"] == "trade_cycle":
            last_run = status.get("last_run_at")
            detail = f"活跃雇佣 {status.get('active_hires', 0)}"

        items.append({
            **t,
            "running": t["key"] == "trade_cycle" and status.get("running", False),
            "last_run": last_run,
            "detail": detail,
        })

    return {
        "code": 0,
        "data": {
            "tasks": items,
            "scheduler_running": status.get("running", False),
        },
        "message": "ok",
    }


@router.post("/trigger")
async def trigger_task(
    task: str = Query(description="daily_picks / daily_backtest"),
    market: str = Query(default="A", description="仅 daily_picks 使用"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("schedule:trigger")),
):
    """手动触发补跑：调用现有 service 层，不侵入引擎算法"""
    if task not in ("daily_picks", "daily_backtest"):
        raise HTTPException(status_code=400, detail="task 仅支持 daily_picks / daily_backtest")

    try:
        if task == "daily_picks":
            result = await refresh_daily_picks(market=market, top_n=5, engine="committee_llm")
            await _log(db, admin, "schedule", "trigger", f"手动触发补跑每日推荐 market={market} success={result.get('success')}")
            await db.commit()
            if not result.get("success"):
                return {"code": 1, "data": result, "message": result.get("error") or "触发失败"}
            return {"code": 0, "data": {"task": task, "result": result}, "message": "ok"}
        else:
            result = await run_daily_backtest()
            await _log(db, admin, "schedule", "trigger", f"手动触发补跑回测 result={str(result)[:300]}")
            await db.commit()
            return {"code": 0, "data": {"task": task, "result": result}, "message": "ok"}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"触发失败: {exc}")
