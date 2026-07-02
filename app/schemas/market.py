"""
app/schemas/market.py — 行情数据 Schema
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class QuoteItem(BaseModel):
    """实时行情条目"""

    symbol: str  # 股票代码，如 "600519.SH"
    name: str  # 股票名称
    price: float  # 当前价
    open: float  # 今开
    high: float  # 最高
    low: float  # 最低
    close: Optional[float] = None  # 昨收（AkShare 实时行情无此字段）
    change: float  # 涨跌额
    change_pct: float  # 涨跌幅（%）
    volume: int  # 成交量（手）
    amount: float  # 成交额（元）
    turnover_rate: Optional[float] = None  # 换手率（%）
    pe_ratio: Optional[float] = None  # 市盈率
    market_cap: Optional[float] = None  # 总市值（亿元）


class QuoteResponse(BaseModel):
    """行情报价响应"""

    success: bool = True
    data: List[QuoteItem]
    note: Optional[str] = None


class KLineItem(BaseModel):
    """K线数据条目"""

    date: str  # 日期，如 "2024-01-01"
    open: float
    close: float
    high: float
    low: float
    volume: int  # 成交量（手）
    amount: Optional[float] = None  # 成交额（元）
    amplitude: Optional[float] = None  # 振幅（%）
    change_pct: Optional[float] = None  # 涨跌幅（%）
    change: Optional[float] = None  # 涨跌额
    turnover_rate: Optional[float] = None  # 换手率（%）


class KLineResponse(BaseModel):
    """K线数据响应"""

    success: bool = True
    symbol: str
    period: str
    data: List[KLineItem]
    note: Optional[str] = None
