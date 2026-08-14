# -*- coding: utf-8 -*-
"""app/services/daily_backtest_service.py — 每日推荐回测闭环

机制：
- 每次每日推荐生成时，逐票写入 pick_tracking（由 daily_picks_service 负责）
- 每天 16:30 由调度器触发本服务：对已到期（T+5 / T+20）的推荐票
  回填入场价、区间收益与基准超额收益
- 基准：A股 = 沪深300 (000300.SH)，港股 = 恒生指数 (HSI)
"""
import logging
from datetime import date, datetime, timezone

from sqlalchemy import select

from app.core.database import get_scheduler_db_context
from app.models.pick_tracking import PickTracking
from app.services.market import fetch_kline

logger = logging.getLogger(__name__)

# 基准指数代码
BENCHMARK_A = "000300.SH"   # 沪深300
BENCHMARK_HK = "HSI"        # 恒生指数

# 回测窗口
T5 = 5
T20 = 20


def _pct(entry: float, exit_: float) -> float | None:
    if not entry or entry <= 0 or exit_ is None:
        return None
    return round((exit_ - entry) / entry * 100, 4)


async def _get_close_by_offset(symbol: str, trade_date: str, offset: int) -> tuple[float | None, float | None]:
    """获取 trade_date 当日收盘价(入场)与 offset 个交易日后收盘价。

    Returns:
        (entry_close, target_close)，取不到返回 (None, None)
    """
    try:
        klines = await fetch_kline(symbol, period="daily", count=40)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[backtest] %s K线获取失败: %s", symbol, exc)
        return None, None

    # klines 按日期升序
    idx_entry = None
    for i, k in enumerate(klines):
        if k.date >= trade_date:
            idx_entry = i
            break
    if idx_entry is None:
        return None, None

    entry_close = klines[idx_entry].close
    idx_target = idx_entry + offset
    if idx_target >= len(klines):
        return entry_close, None
    return entry_close, klines[idx_target].close


async def _get_benchmark_close(market: str, trade_date: str, offset: int) -> float | None:
    """获取基准指数 offset 个交易日后的收盘价。"""
    benchmark = BENCHMARK_A if market == "A" else BENCHMARK_HK
    _, target = await _get_close_by_offset(benchmark, trade_date, offset)
    return target


async def run_daily_backtest() -> dict:
    """执行每日回测：扫描到期未回填的 pick_tracking 记录并更新。"""
    today = date.today()
    stats = {"scanned": 0, "updated": 0, "t5_done": 0, "t20_done": 0, "errors": 0}

    async with get_scheduler_db_context() as db:
        result = await db.execute(
            select(PickTracking).where(
                PickTracking.t5_return.is_(None) | PickTracking.t20_return.is_(None)
            ).order_by(PickTracking.trade_date.desc()).limit(100)
        )
        records = result.scalars().all()
        stats["scanned"] = len(records)

        for rec in records:
            try:
                trade_date_str = rec.trade_date
                updated = False

                # T+5
                if rec.t5_return is None:
                    entry, target = await _get_close_by_offset(rec.symbol, trade_date_str, T5)
                    if entry and target:
                        rec.entry_price = entry
                        rec.t5_return = _pct(entry, target)
                        bench = await _get_benchmark_close(rec.market, trade_date_str, T5)
                        if bench is not None:
                            bench_entry, _ = await _get_close_by_offset(
                                BENCHMARK_A if rec.market == "A" else BENCHMARK_HK,
                                trade_date_str, 0,
                            )
                            if bench_entry:
                                rec.t5_benchmark_return = _pct(bench_entry, bench)
                        stats["t5_done"] += 1
                        updated = True

                # T+20
                if rec.t20_return is None:
                    entry, target = await _get_close_by_offset(rec.symbol, trade_date_str, T20)
                    if entry and target:
                        if rec.entry_price is None:
                            rec.entry_price = entry
                        rec.t20_return = _pct(entry, target)
                        bench = await _get_benchmark_close(rec.market, trade_date_str, T20)
                        if bench is not None:
                            bench_entry, _ = await _get_close_by_offset(
                                BENCHMARK_A if rec.market == "A" else BENCHMARK_HK,
                                trade_date_str, 0,
                            )
                            if bench_entry:
                                rec.t20_benchmark_return = _pct(bench_entry, bench)
                        stats["t20_done"] += 1
                        updated = True

                if updated:
                    rec.backtest_updated_at = datetime.now(timezone.utc)
                    stats["updated"] += 1
            except Exception as exc:  # noqa: BLE001
                stats["errors"] += 1
                logger.error("[backtest] 回测失败 symbol=%s date=%s: %s", rec.symbol, rec.trade_date, exc)

        await db.commit()

    logger.info("[backtest] 回测完成: %s", stats)
    return {"success": True, "date": today.isoformat(), **stats}
