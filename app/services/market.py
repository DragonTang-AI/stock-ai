"""
app.services.market — 行情数据服务（v2：使用 adapter 架构）

改造点（v1 → v2）：
1. 不再直接 import akshare，改为通过 app.integrations.market_data 获取 adapter
2. 保持原有接口（fetch_realtime_quotes / fetch_kline）向后兼容
3. QuoteData / KLineData → 转换为 API schema (QuoteItem / KLineItem)

数据源选择：
- 默认自动降级：akshare → sina → mock
- 通过环境变量 MARKET_DATA_SOURCE=sina/akshare/mock 显式指定
- 服务器目前无法用 akshare（Python 3.12 兼容性问题），所以默认会走到 sina
"""
import logging
from typing import List

from app.schemas.market import QuoteItem, KLineItem
from app.integrations.market_data import get_market_data_adapter
from app.integrations.market_data.base import (
    QuoteData as AdapterQuoteData,
    KLineData as AdapterKLineData,
)

logger = logging.getLogger(__name__)


def _quote_to_item(q: AdapterQuoteData) -> QuoteItem:
    """Adapter 数据模型 → API 响应模型"""
    return QuoteItem(
        symbol=q.symbol,
        name=q.name,
        price=q.price,
        open=q.open,
        high=q.high,
        low=q.low,
        close=q.prev_close,  # 字段名差异：prev_close → close
        change=q.change,
        change_pct=q.change_pct,
        volume=q.volume,
        amount=q.amount,
        turnover_rate=q.turnover_rate,
        pe_ratio=q.pe_ratio,
        market_cap=q.market_cap,
    )


def _kline_to_item(k: AdapterKLineData) -> KLineItem:
    """Adapter 数据模型 → API 响应模型"""
    return KLineItem(
        date=k.date,
        open=k.open,
        close=k.close,
        high=k.high,
        low=k.low,
        volume=k.volume,
        amount=k.amount,
        amplitude=k.amplitude,
        change_pct=k.change_pct,
        change=k.change,
        turnover_rate=k.turnover_rate,
    )


async def fetch_realtime_quotes(symbols: List[str]) -> List[QuoteItem]:
    """
    获取实时行情报价（向后兼容方法）

    通过 adapter 抽象获取数据，业务层不再关心具体数据源。

    Args:
        symbols: 股票代码列表，如 ["600519.SH", "000001.SZ"]

    Returns:
        QuoteItem 列表
    """
    adapter = get_market_data_adapter()
    logger.debug(f"使用 {adapter.name} adapter 获取 {len(symbols)} 只股票行情")

    quotes = await adapter.get_quotes(symbols)
    return [_quote_to_item(q) for q in quotes]


async def fetch_kline(
    symbol: str,
    period: str = "daily",
    count: int = 100,
) -> List[KLineItem]:
    """
    获取 K 线历史数据（向后兼容方法）

    Args:
        symbol: 股票代码，如 "600519.SH"
        period: 周期，"daily"/"weekly"/"monthly"
        count: 返回条数

    Returns:
        KLineItem 列表（按日期升序）
    """
    from app.integrations.market_data.base import Period

    period_map = {
        "daily": Period.DAILY,
        "weekly": Period.WEEKLY,
        "monthly": Period.MONTHLY,
    }
    ak_period = period_map.get(period, Period.DAILY)

    adapter = get_market_data_adapter()
    logger.debug(f"使用 {adapter.name} adapter 获取 {symbol} K线 ({period}, {count}条)")

    klines = await adapter.get_kline(symbol, ak_period, count)
    return [_kline_to_item(k) for k in klines]
