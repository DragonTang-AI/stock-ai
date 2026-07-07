"""
app.tasks.kline_scheduler — 每日 K 线采集任务（P1-F4）

职责：
1. 每交易日 16:05 触发（systemd timer）
2. 获取候选池（prescreen 134 只 + 用户自选股）
3. 并发拉新浪 K 线（限制并发 5，避免限流）
4. upsert 到 market.kline_daily

用法：
- 定时触发：systemd timer 调用 `python -m app.tasks.kline_scheduler`
- 手动回填：python scripts/backfill_kline.py --days 250 --concurrency 5

设计原则：不跳步、选股零 LLM、异常隔离（单只失败不影响整体）
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Set

from sqlalchemy import select, distinct
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import get_session_factory
from app.models.kline import DailyKline
from app.integrations.market_data.base import Period
from app.integrations.market_data import get_market_data_adapter

logger = logging.getLogger(__name__)

# 可配置参数（backfill 脚本会覆盖）
KLINE_DAYS = 250
CONCURRENCY = 5


async def _get_candidate_symbols() -> List[str]:
    """获取候选池：prescreen 池 + 自选股（去重）"""
    symbols: Set[str] = set()

    # 1. prescreen 池（A + HK）
    try:
        from app.services.prescreen_service import A_STOCK_POOL, EXTENDED_POOL
        symbols.update(A_STOCK_POOL)
        symbols.update(EXTENDED_POOL)
    except Exception as e:
        logger.warning(f"[kline] prescreen 池加载失败: {e}")

    # 2. 用户自选股
    try:
        from app.models.stock import Watchlist
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(select(distinct(Watchlist.symbol)))
            for r in result.all():
                symbols.add(r[0])
    except Exception as e:
        logger.warning(f"[kline] 自选股加载失败: {e}")

    return list(symbols)


async def collect_klines_for_symbol(
    adapter, symbol: str, market: str = "A", days: int = KLINE_DAYS
) -> int:
    """
    拉一只股票的 K 线并 upsert 到 DB

    Returns:
        写入/更新的条数
    """
    try:
        klines = await adapter.get_kline(symbol, period=Period.DAILY, count=days)
    except Exception as e:
        logger.warning(f"[kline] 拉取失败 {symbol}: {e}")
        return 0

    if not klines:
        return 0

    rows = []
    for k in klines:
        try:
            rows.append({
                "symbol": symbol,
                "trade_date": (k.date or "")[:10],
                "market": market,
                "open": float(k.open),
                "high": float(k.high),
                "low": float(k.low),
                "close": float(k.close),
                "volume": float(k.volume or 0),
                "amount": float(k.amount or 0),
            })
        except (ValueError, TypeError) as e:
            logger.warning(f"[kline] 数据行解析失败 {symbol}: {e}")
            continue

    if not rows:
        return 0

    # upsert（OnConflict(symbol, trade_date, market) DO UPDATE）
    stmt = pg_insert(DailyKline).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "trade_date", "market"],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
            "amount": stmt.excluded.amount,
        },
    )

    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(stmt)
            await session.commit()
        return len(rows)
    except Exception as e:
        logger.error(f"[kline] 写入失败 {symbol}: {e}")
        return 0


async def run_daily_kline_collection(days: int = KLINE_DAYS) -> dict:
    """
    主入口：并发采集全部候选池

    Returns:
        {"total": N, "success": M, "rows": K}
    """
    adapter = get_market_data_adapter()
    symbols = await _get_candidate_symbols()
    logger.info(f"[kline] 开始采集，候选 {len(symbols)} 只，回溯 {days} 日")

    sem = asyncio.Semaphore(CONCURRENCY)

    async def _task(sym: str):
        async with sem:
            return await collect_klines_for_symbol(adapter, sym, days=days)

    results = await asyncio.gather(*[_task(s) for s in symbols], return_exceptions=True)

    success = 0
    total_rows = 0
    for r in results:
        if isinstance(r, Exception):
            logger.error(f"[kline] 采集异常: {r}")
            continue
        if isinstance(r, int) and r > 0:
            success += 1
            total_rows += r

    logger.info(f"[kline] 采集完成：{success}/{len(symbols)} 成功，共 {total_rows} 条")
    return {"total": len(symbols), "success": success, "rows": total_rows}


def main():
    """CLI 入口（供 systemd service 调用）"""
    logging.basicConfig(level=logging.INFO)
    start = datetime.now()
    result = asyncio.run(run_daily_kline_collection(KLINE_DAYS))
    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"[kline] 总耗时 {elapsed:.1f}s，结果: {result}")


if __name__ == "__main__":
    main()
