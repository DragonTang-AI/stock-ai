"""
scheduler.py — 智能调度器 v2

Features:
- 全托管/建议双模式自动运行
- 全托管：自动生成信号 → 自动执行交易
- 建议模式：自动生成信号 → 前端展示待处理
- 超时保护：每个 hire 独立超时，不互相卡死
- 独立DB会话：每个 hire 使用独立 DB session，避免并发冲突
- 状态追踪：前端可查询调度器运行状态
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import Any

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_scheduler_db_context as get_db_context
from app.models.agent import UserAgent, AgentTrader, AgentSignal, AgentConfig
from app.engine import signal_generator
from app.engine.auto_executor import auto_execute_signals
from app.engine.market_hours import is_any_market_hours
from app.services.agent_config_service import get_agent_config, DEFAULTS as CONFIG_DEFAULTS

logger = logging.getLogger(__name__)

# ── 调度配置 ──

# 开发期：每 5 分钟运行一次
DEV_INTERVAL_SECONDS = 5 * 60

# A 股交易时段
PRE_MARKET_TIME = dt_time(9, 0)
MARKET_OPEN_TIME = dt_time(9, 30)
MARKET_CLOSE_TIME = dt_time(15, 0)
POST_MARKET_TIME = dt_time(15, 30)



# 单个 hire 信号生成超时（秒）
PER_HIRE_TIMEOUT = 180

# 并发控制：同时最多处理 N 个 hire，防止并行打爆 LLM API 导致全员超时
MAX_CONCURRENT_HIRES = 4
_hire_semaphore = asyncio.Semaphore(MAX_CONCURRENT_HIRES)

# ── 调度器状态 ──

_scheduler_running = False
_tasks: list[asyncio.Task] = []
_scheduler_status: dict[str, Any] = {
    "running": False,
    "last_run_at": None,
    "next_run_at": None,
    "last_run_result": None,
    "active_hires": 0,
    "current_phase": "idle",
}


def get_status() -> dict[str, Any]:
    """获取调度器当前状态（供 API 查询）"""
    return dict(_scheduler_status)


async def _get_active_hires(db: AsyncSession) -> list[dict]:
    """获取所有活跃雇佣关系"""
    result = await db.execute(
        select(UserAgent, AgentTrader).join(
            AgentTrader, AgentTrader.id == UserAgent.agent_id
        ).where(UserAgent.status == "active")
    )
    rows = result.all()
    return [
        {
            "hire_id": hire.id,
            "user_id": hire.user_id,
            "agent_id": hire.agent_id,
            "trader_id": trader.id,
            "management_mode": hire.management_mode,
            "trader_name": trader.code_name,
        }
        for hire, trader in rows
    ]


async def _process_single_hire(hire: dict) -> dict[str, Any]:
    """并发受限入口：同时最多 MAX_CONCURRENT_HIRES 个 hire 在处理"""
    async with _hire_semaphore:
        return await _process_single_hire_impl(hire)


async def _process_single_hire_impl(hire: dict) -> dict[str, Any]:
    """
    处理单个活跃雇佣关系：生成信号 + 自动执行
    使用独立的 DB session，避免并发冲突
    """
    hire_id = hire["hire_id"]
    trader_name = hire.get("trader_name", f"#{hire_id}")
    management_mode = hire.get("management_mode", "advisory")

    async with get_db_context() as db:
        try:
            # P1: 读取配置，信号间隔从 agent_configs 获取
            agent_config = await get_agent_config(db, hire_id)
            min_interval_seconds = (
                agent_config.signal_interval_min * 60
                if agent_config and agent_config.signal_interval_min
                else CONFIG_DEFAULTS["signal_interval_min"] * 60
            )

            # 检查最小间隔
            result = await db.execute(
                select(func.max(AgentSignal.created_at)).where(
                    AgentSignal.hire_id == hire_id
                )
            )
            last_time = result.scalar()
            now = datetime.now(timezone.utc)
            if last_time and (now - last_time).total_seconds() < min_interval_seconds:
                return {
                    "hire_id": hire_id,
                    "trader_name": trader_name,
                    "mode": management_mode,
                    "status": "skipped",
                    "reason": f"距上次生成仅 {(now - last_time).total_seconds():.0f}s",
                }

            # 生成信号（带超时）
            gen_result = await asyncio.wait_for(
                signal_generator.generate_signals(
                    db=db,
                    hire_id=hire_id,
                    user_id=hire["user_id"],
                ),
                timeout=PER_HIRE_TIMEOUT,
            )

            signals = gen_result.get("signals", [])
            source = gen_result.get("source", "unknown")
            rejected = gen_result.get("rejected_count", 0)
            demo_mode = gen_result.get("demo_mode", False)

            logger.info(
                "调度 #%d [%s] %s: 生成 %d 条信号 (source=%s, rejected=%d, demo=%s)",
                hire_id, trader_name, management_mode, len(signals), source, rejected, demo_mode,
            )

            if not signals:
                return {
                    "hire_id": hire_id,
                    "trader_name": trader_name,
                    "mode": management_mode,
                    "source": source,
                    "signals_count": 0,
                    "status": "no_signals",
                }

            # P2-11: mock 演示模式禁止 full_managed 自动执行，只保留为 pending 供前端展示
            if management_mode == "full_managed" and demo_mode:
                logger.warning(
                    "调度 #%d [%s] full_managed 收到演示模式信号，禁止自动下单（source=mock）",
                    hire_id, trader_name,
                )
                return {
                    "hire_id": hire_id,
                    "trader_name": trader_name,
                    "mode": management_mode,
                    "source": source,
                    "demo_mode": True,
                    "signals_count": len(signals),
                    "executed_count": 0,
                    "pending_count": len(signals),
                    "failed_count": 0,
                    "status": "demo_mode_skipped",
                }

            # 自动执行
            exec_result = await auto_execute_signals(
                db=db,
                hire_id=hire_id,
                user_id=hire["user_id"],
                signals=signals,
                management_mode=management_mode,
                config=agent_config,
            )

            executed = exec_result.get("executed", [])
            pending = exec_result.get("pending", [])
            failed = exec_result.get("failed", [])

            if management_mode == "full_managed" and executed:
                logger.info(
                    "  全托管自动执行: %d 条, 待确认: %d 条",
                    len(executed), len(pending),
                )
            elif management_mode == "advisory":
                logger.info("  建议模式: %d 条待用户确认", len(signals))

            return {
                "hire_id": hire_id,
                "trader_name": trader_name,
                "mode": management_mode,
                "source": source,
                "signals_count": len(signals),
                "executed_count": len(executed),
                "pending_count": len(pending),
                "failed_count": len(failed),
                "status": "done",
            }

        except asyncio.TimeoutError:
            logger.error("调度 #%d [%s] 超时 (>%ds)，跳过", hire_id, trader_name, PER_HIRE_TIMEOUT)
            return {
                "hire_id": hire_id,
                "trader_name": trader_name,
                "mode": management_mode,
                "status": "timeout",
            }
        except Exception as e:
            logger.error("调度 #%d [%s] 异常: %s", hire_id, trader_name, str(e))
            return {
                "hire_id": hire_id,
                "trader_name": trader_name,
                "mode": management_mode,
                "status": "error",
                "error": str(e),
            }


async def _expire_stale_hires():
    """P2-13: 将已到期的 active hire 自动标为 expired，停止调度"""
    try:
        async with get_db_context() as db:
            from sqlalchemy import update as sa_update
            now = datetime.now(timezone.utc)
            result = await db.execute(
                sa_update(UserAgent)
                .where(
                    UserAgent.status == "active",
                    UserAgent.expires_at.is_not(None),
                    UserAgent.expires_at < now,
                )
                .values(status="expired", updated_at=now)
            )
            await db.commit()
            if result.rowcount:
                logger.info("自动过期 %d 个已到期雇佣关系", result.rowcount)
    except Exception as e:
        logger.error("到期清理失败: %s", str(e))


async def _expire_stale_pending():
    """将超过 24h 的 pending 信号自动标记为 expired，防止无限堆积"""
    try:
        async with get_db_context() as db:
            from sqlalchemy import update as sa_update
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            result = await db.execute(
                sa_update(AgentSignal)
                .where(
                    AgentSignal.exec_status == "pending",
                    AgentSignal.created_at < cutoff,
                )
                .values(exec_status="expired", updated_at=datetime.now(timezone.utc))
            )
            await db.commit()
            if result.rowcount:
                logger.info("自动过期 %d 条超过24h的pending信号", result.rowcount)
    except Exception as e:
        logger.error("过期清理失败: %s", str(e))


async def _run_one_cycle():
    """执行一次完整的调度周期"""
    global _scheduler_status

    _scheduler_status["current_phase"] = "running"
    start_time = time.time()

    # 到期清理：自动过期到期的雇佣关系（不依赖交易时段）
    await _expire_stale_hires()

    # 过期清理：超过 24h 的 pending 信号自动标 expired（不依赖交易时段）
    await _expire_stale_pending()

    # 非交易时段跳过（A 股或港股任一交易时段均允许运行）
    if not is_any_market_hours():
        logger.info("非交易时段，跳过本次调度")
        _scheduler_status["current_phase"] = "idle"
        _scheduler_status["next_run_at"] = (datetime.now(timezone.utc) + timedelta(seconds=DEV_INTERVAL_SECONDS)).isoformat().replace("+00:00", "Z")
        return
    

    try:
        async with get_db_context() as db:
            hires = await _get_active_hires(db)
            _scheduler_status["active_hires"] = len(hires)

        if not hires:
            logger.info("调度: 无活跃雇佣关系")
            now = datetime.now(timezone.utc)
            _scheduler_status["last_run_at"] = now.isoformat().replace("+00:00", "Z")
            _scheduler_status["next_run_at"] = (now + timedelta(seconds=DEV_INTERVAL_SECONDS)).isoformat().replace("+00:00", "Z")
            _scheduler_status["last_run_result"] = {"total": 0, "items": []}
            _scheduler_status["current_phase"] = "idle"
            return

        # 并行处理所有 hires（每个使用独立 DB session）
        tasks = [_process_single_hire(hire) for hire in hires]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        items = []
        for hire, result in zip(hires, results):
            if isinstance(result, Exception):
                items.append({
                    "hire_id": hire["hire_id"],
                    "trader_name": hire.get("trader_name", ""),
                    "mode": hire.get("management_mode", "advisory"),
                    "status": "error",
                    "error": str(result),
                })
            else:
                items.append(result)

        total_signals = sum(r.get("signals_count", 0) for r in items)
        total_executed = sum(r.get("executed_count", 0) for r in items)
        total_pending = sum(r.get("pending_count", 0) for r in items)
        errors = [r for r in items if r.get("status") in ("error", "timeout")]

        elapsed = time.time() - start_time
        logger.info(
            "调度周期完成: %d 活跃, %d 信号, %d 执行, %d 待确认, %d 异常, %.1fs",
            len(hires), total_signals, total_executed, total_pending, len(errors), elapsed,
        )

        _scheduler_status.update({
            "last_run_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "next_run_at": (datetime.now(timezone.utc) + timedelta(seconds=DEV_INTERVAL_SECONDS)).isoformat().replace("+00:00", "Z"),
            "last_run_result": {
                "total_hires": len(hires),
                "total_signals": total_signals,
                "total_executed": total_executed,
                "total_pending": total_pending,
                "errors": len(errors),
                "elapsed_seconds": round(elapsed, 1),
                "items": items,
            },
        })

    except Exception as e:
        logger.error("调度周期异常: %s", str(e))
        _scheduler_status["last_run_result"] = {"error": str(e)}

    finally:
        _scheduler_status["current_phase"] = "idle"


async def _scheduler_loop():
    """调度主循环"""
    global _scheduler_running
    _scheduler_running = True
    _scheduler_status["running"] = True

    logger.info(
        "[Scheduler v2] 启动 (间隔=%ds, 单hire超时=%ds)",
        DEV_INTERVAL_SECONDS, PER_HIRE_TIMEOUT,
    )

    while _scheduler_running:
        try:
            await _run_one_cycle()
        except Exception as e:
            logger.error("[Scheduler] 主循环异常: %s", str(e))

        await asyncio.sleep(DEV_INTERVAL_SECONDS)


async def start_scheduler():
    """启动调度器"""
    global _tasks, _scheduler_running

    if _scheduler_running:
        logger.warning("[Scheduler] 已在运行中")
        return

    task = asyncio.create_task(_scheduler_loop())
    _tasks.append(task)
    logger.info("[Scheduler v2] 已启动")


async def stop_scheduler():
    """停止调度器"""
    global _scheduler_running, _tasks
    _scheduler_running = False
    _scheduler_status["running"] = False

    for t in _tasks:
        t.cancel()

    if _tasks:
        await asyncio.gather(*_tasks, return_exceptions=True)
    _tasks.clear()
    logger.info("[Scheduler] 已停止")


def is_running() -> bool:
    return _scheduler_running
