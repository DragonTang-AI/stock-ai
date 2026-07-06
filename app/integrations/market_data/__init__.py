"""
app.integrations.market_data — 行情数据源集成

支持的实现：
- SinaAdapter: 新浪财经 HTTP API（首选，零依赖，零兼容性问题）
- AkshareAdapter: AkShare 库（fallback，需要 py_mini_racer 等依赖）
- MockAdapter: Mock 数据（测试/降级使用）

通过 factory.py 中的 get_market_data_adapter() 获取默认实现。
"""
from app.integrations.market_data.base import (
    MarketDataAdapter,
    QuoteData,
    KLineData,
    Period,
)
from app.integrations.market_data.factory import get_market_data_adapter

__all__ = [
    "MarketDataAdapter",
    "QuoteData",
    "KLineData",
    "Period",
    "get_market_data_adapter",
]
