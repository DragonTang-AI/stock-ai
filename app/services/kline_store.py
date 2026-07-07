"""
app.services.kline_store — K 线读取服务（P1-F4）

核心职责：
- 统一 K 线读取入口
- 优先从 market.kline_daily 读（持久化后秒级返回）
- DB 无数据则 fallback 拉新浪（兼容旧逻辑 & 未采集标的）

设计原则（Opus 定稿 5 原则）：
- 不跳步：读不到 DB 也不报错，降级到数据源
- 选股零 LLM：K 线数据纯行情，无 AI 依赖
"""
import logging
from typing import List, Optional

from sqlalchemy import select

from app.core.database import get_session_factory
from app.models.kline import DailyKline
from app.schemas.market import KLineItem
from app.integrations.market_data.base import Period

logger = logging.getLogger(__name__)


async def get_klines(
    symbol: str,
    count: int = 250,
    market: str = "A",
    period: str = "daily",
) -> List[KLineItem]:
    """
    获取 K 线历史数据（DB 优先）

    Args:
        symbol: 股票代码，如 "600519.SH"
        count: 返回条数（默认 250，覆盖 MA20/RSI/MACD 所需）
        market: 市场标识（A/HK/US）
        period: 周期 daily/weekly/monthly（仅 daily 走 DB，其余 fallback 新浪）

    Returns:
        KLineItem 列表（按日期升序）
    """
    # 非日线直接从新浪拉（DB 仅存日线）
    if period != "daily":
        return await _fetch_from_sina(symbol, period, count)

    # 优先读 DB
    try:
        rows = await _read_from_db(symbol, count, market)
        if rows:
            return rows
    except Exception as e:
        logger.warning(f"[kline_store] DB 读取失败 {symbol}: {e}，fallback 新浪")

    # Fallback 新浪
    return await _fetch_from_sina(symbol, "daily", count)


async def _read_from_db(symbol: str, count: int, market: str) -> List[KLineItem]:
    """从 market.kline_daily 读取（按日期降序取前 N，再反转成升序）"""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(DailyKline)
            .where(DailyKline.symbol == symbol, DailyKline.market == market)
            .order_by(DailyKline.trade_date.desc())
            .limit(count)
        )
        rows = result.scalars().all()

    if not rows:
        return []

    # DB 降序 → 反转成升序（KLineItem 期望时间升序）
    rows = list(reversed(rows))
    return [
        KLineItem(
            date=r.trade_date,
            open=float(r.open),
            close=float(r.close),
            high=float(r.high),
            low=float(r.low),
            volume=int(r.volume or 0),
            amount=float(r.amount or 0.0),
        )
        for r in rows
    ]


async def _fetch_from_sina(symbol: str, period: str, count: int) -> List[KLineItem]:
    """从新浪拉 K 线（fallback 路径）"""
    from app.services.market import fetch_kline

    period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
    p = period_map.get(period, "daily")
    try:
        return await fetch_kline(symbol, period=p, count=count)
    except Exception as e:
        logger.warning(f"[kline_store] 新浪拉取失败 {symbol}: {e}")
        return []


async def count_klines(symbol: str, market: str = "A") -> int:
    """统计某标的 K 线条数（用于回填进度检查）"""
    from sqlalchemy import func

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(func.count())
            .select_from(DailyKline)
            .where(DailyKline.symbol == symbol, DailyKline.market == market)
        )
        return result.scalar() or 0
