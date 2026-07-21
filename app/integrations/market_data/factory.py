"""
app.integrations.market_data.factory — 数据源工厂
"""
import logging
from typing import List

from .base import MarketDataAdapter
from .sina import SinaAdapter

logger = logging.getLogger(__name__)


def get_market_data_adapter(name: str = "sina") -> MarketDataAdapter:
    if name == "sina":
        return SinaAdapter()
    raise ValueError(f"Unknown provider: {name}")
