"""
scheduler.py — 定时调度器

使用 asyncio 定时任务调度 ai-hedge-fund 分析：
- 盘前（9:00）：预热分析，生成当日候选信号
- 盘中（9:30-15:00，每30分钟）：增量分析 + 信号更新
- 盘后（15:30）：结算当日收益，更新权益曲线

启动时自动注册到 FastAPI 的 lifespan。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_context
from app.models.agent import UserAgent
from app.engine import signal_generator

logger = logging.getLogger(__name__)

# ── 定时任务配置 ──

PRE_MARKET_TIME = time(9, 0)       # 盘前分析
MARKET_OPEN_TIME = time(9, 30)     # 盘中开始
MARKET_CLOSE_TIME = time(15, 0)    # 盘中结束
POST_MARKET_TIME = time(15, 30)    # 盘后结算
INTRADAY_INTERVAL = 30 * 60        # 盘中每 30 分钟

# 控制开关
_scheduler_running = False
_tasks: list[asyncio.Task] = []


async def _get_active_hires(db: AsyncSession) -> list[dict]:
    """获取所有活跃的雇佣关系"""
    result = await db.execute(
        select(UserAgent).where(UserAgent.status == "active")
    )
    hires = result.scalars().all()
    return [{"hire_id": h.id, "user_id": h.user_id, "agent_id": h.agent_id} for h in hires]


async def _generate_for_all_active(db: AsyncSession):
    """为所有活跃雇佣关系生成信号"""
    hires = await _get_active_hires(db)
    logger.info("定时调度：为 %d 个活跃雇佣关系生成信号", len(hires))
    for h in hires:
        try:
            result = await signal_generator.generate_signals(
                db=db, hire_id=h["hire_id"], user_id=h["user_id"]
            )
            logger.info(
                "  雇佣 #%d: 生成 %d 条信号 (source=%s, rejected=%d)",
                h["hire_id"],
                len(result["signals"]),
                result["source"],
                result["rejected_count"],
            )
        except Exception as e:
            logger.error("  雇佣 #%d 信号生成失败: %s", h["hire_id"], str(e))


async def _pre_market_job():
    """盘前任务：预热分析"""
    logger.info("[Scheduler] 盘前分析开始")
    async with get_db_context() as db:
        await _generate_for_all_active(db)
    logger.info("[Scheduler] 盘前分析完成")


async def _intraday_job():
    """盘中任务：增量分析"""
    logger.info("[Scheduler] 盘中增量分析开始")
    async with get_db_context() as db:
        await _generate_for_all_active(db)
    logger.info("[Scheduler] 盘中增量分析完成")


async def _post_market_job():
    """盘后任务：结算收益"""
    logger.info("[Scheduler] 盘后结算开始")
    # 结算逻辑：当前 Phase 3 先记录日志，后续 Phase 扩展
    async with get_db_context() as db:
        hires = await _get_active_hires(db)
        logger.info("[Scheduler] 盘后结算：共 %d 个活跃交易员需要结算", len(hires))
    logger.info("[Scheduler] 盘后结算完成")


def _should_run(target_time: time) -> bool:
    """检查当前是否在目标时间的合理窗口内（前后 2 分钟）"""
    now = datetime.now().time()
    target_minutes = target_time.hour * 60 + target_time.minute
    now_minutes = now.hour * 60 + now.minute
    return abs(now_minutes - target_minutes) <= 2


async def _scheduler_loop():
    """调度主循环，每分钟检查一次"""
    global _scheduler_running
    _scheduler_running = True

    logger.info("[Scheduler] 调度器已启动（盘前 9:00 / 盘中每30分钟 / 盘后 15:30）")

    last_intraday_run: datetime | None = None

    while _scheduler_running:
        try:
            now = datetime.now()
            weekday = now.weekday()

            # 周末不执行
            if weekday >= 5:
                await asyncio.sleep(60)
                continue

            # 盘前
            if _should_run(PRE_MARKET_TIME):
                await _pre_market_job()
                await asyncio.sleep(120)  # 避免同一分钟重复执行

            # 盘中（每 30 分钟）
            if MARKET_OPEN_TIME <= now.time() <= MARKET_CLOSE_TIME:
                if last_intraday_run is None or (now - last_intraday_run).total_seconds() >= INTRADAY_INTERVAL:
                    await _intraday_job()
                    last_intraday_run = now

            # 盘后
            if _should_run(POST_MARKET_TIME):
                await _post_market_job()
                await asyncio.sleep(120)

        except Exception as e:
            logger.error("[Scheduler] 调度循环异常: %s", str(e))

        await asyncio.sleep(60)


async def start_scheduler():
    """启动调度器（由 FastAPI lifespan 调用）"""
    global _tasks, _scheduler_running

    if _scheduler_running:
        logger.warning("[Scheduler] 调度器已在运行中")
        return

    task = asyncio.create_task(_scheduler_loop())
    _tasks.append(task)
    logger.info("[Scheduler] 调度器已启动")


async def stop_scheduler():
    """停止调度器"""
    global _scheduler_running, _tasks
    _scheduler_running = False

    for t in _tasks:
        t.cancel()

    if _tasks:
        await asyncio.gather(*_tasks, return_exceptions=True)
    _tasks.clear()
    logger.info("[Scheduler] 调度器已停止")


def is_running() -> bool:
    return _scheduler_running
