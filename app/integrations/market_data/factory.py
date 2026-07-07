"""
app.integrations.market_data.factory — Adapter 工厂

根据环境变量选择合适的 adapter，提供：
1. 显式选择（环境变量 MARKET_DATA_SOURCE=sina/akshare/mock）
2. 自动降级（按优先级尝试：akshare → sina → mock）
3. 单例缓存（同一 source 只创建一个实例）

使用方式：
    from app.integrations.market_data import get_market_data_adapter

    adapter = get_market_data_adapter()
    quotes = await adapter.get_quotes(["600519.SH", "000001.SZ"])
"""
import logging
import os
from functools import lru_cache
from typing import Optional

from app.integrations.market_data.base import MarketDataAdapter
from app.integrations.market_data.sina import SinaAdapter
from app.integrations.market_data.akshare import AkshareAdapter, is_akshare_available

logger = logging.getLogger(__name__)

# Mock adapter：用于测试和开发环境
class MockAdapter(MarketDataAdapter):
    """Mock 数据源，用于测试和开发"""

    name = "mock"

    async def get_quote(self, symbol: str) -> "MockQuote":  # type: ignore
        from app.integrations.market_data.base import QuoteData

        # 简单的 Mock 数据
        return QuoteData(
            symbol=symbol,
            name=f"Mock-{symbol}",
            price=100.0,
            open=99.0,
            high=101.0,
            low=98.0,
            prev_close=99.5,
            change=0.5,
            change_pct=0.5,
            volume=1000000,
            amount=100000000.0,
        )

    async def get_quotes(self, symbols):
        return [await self.get_quote(s) for s in symbols]

    async def get_kline(self, symbol, period=None, count=100):
        from app.integrations.market_data.base import KLineData

        if period is None:
            from app.integrations.market_data.base import Period

            period = Period.DAILY

        import datetime
        results = []
        today = datetime.date.today()
        for i in range(count):
            date = today - datetime.timedelta(days=count - i)
            results.append(
                KLineData(
                    symbol=symbol,
                    date=str(date),
                    period=period,
                    open=100.0 + i * 0.1,
                    close=100.0 + i * 0.1 + 0.5,
                    high=100.0 + i * 0.1 + 1.0,
                    low=100.0 + i * 0.1 - 0.5,
                    volume=1000000,
                )
            )
        return results


def _try_create(source: str) -> Optional[MarketDataAdapter]:
    """尝试创建一个 adapter，失败返回 None"""
    source = source.lower()
    if source == "sina":
        try:
            return SinaAdapter()
        except Exception as e:
            logger.warning(f"创建 SinaAdapter 失败: {e}")
            return None
    elif source == "akshare":
        if not is_akshare_available():
            logger.warning("AkShare 不可用")
            return None
        try:
            return AkshareAdapter()
        except Exception as e:
            logger.warning(f"创建 AkshareAdapter 失败: {e}")
            return None
    elif source == "mock":
        return MockAdapter()
    else:
        logger.warning(f"未知的数据源: {source}")
        return None


@lru_cache(maxsize=1)
def get_market_data_adapter() -> MarketDataAdapter:
    """
    获取行情数据 adapter（单例）

    选择策略（按 MARKET_DATA_SOURCE 环境变量）：
    - 显式指定：直接用指定 source（sina/akshare/mock）
    - 未指定：按优先级尝试 akshare → sina → mock
    """
    source = os.getenv("MARKET_DATA_SOURCE", "").lower()

    if source:
        # 显式指定
        adapter = _try_create(source)
        if adapter is None:
            logger.warning(f"指定的数据源 {source} 不可用，降级到 mock")
            return MockAdapter()
        logger.info(f"使用指定数据源: {source}")
        return adapter

    # 自动降级链：akshare → sina → mock
    for try_source in ("akshare", "sina"):
        adapter = _try_create(try_source)
        if adapter is not None:
            logger.info(f"自动选择数据源: {try_source}")
            return adapter

    # 全部失败，用 mock
    logger.warning("所有真实数据源都不可用，使用 MockAdapter")
    return MockAdapter()


def reset_adapter_cache():
    """重置 adapter 缓存（用于测试或动态切换）"""
    get_market_data_adapter.cache_clear()
