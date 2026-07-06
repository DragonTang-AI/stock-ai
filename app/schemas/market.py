"""
app.schemas.market — 行情数据模型（补充详情页）
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ============== 行情 ==============
class QuoteItem(BaseModel):
    """单只股票行情"""
    symbol: str
    name: str
    price: float
    open: float
    high: float
    low: float
    close: float
    change: float
    change_pct: float
    volume: int
    amount: float
    turnover_rate: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    market_cap: Optional[float] = None
    circul_cap: Optional[float] = None


class QuoteResponse(BaseModel):
    """行情列表响应"""
    success: bool
    data: List[QuoteItem] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)


# ============== K 线 ==============
class KLineItem(BaseModel):
    """K 线数据"""
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: int
    amount: float = 0.0
    amplitude: Optional[float] = None
    change_pct: Optional[float] = None
    change: Optional[float] = None
    turnover_rate: Optional[float] = None


class KLineResponse(BaseModel):
    """K线响应"""
    success: bool
    data: List[KLineItem] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)


# ============== 详情页（新增） ==============
class StockDetail(BaseModel):
    """股票详情（实时行情 + K 线 + 技术指标）"""
    symbol: str
    name: str
    market: str

    # 实时行情
    price: float
    open: float
    high: float
    low: float
    prev_close: float
    change: float
    change_pct: float
    volume: int
    amount: float

    # 财务指标
    turnover_rate: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    market_cap: Optional[float] = None
    circul_cap: Optional[float] = None

    # 技术指标（从 K 线计算）
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    ma5_pct: Optional[float] = None  # 股价相对 MA5 偏离 %
    ma20_pct: Optional[float] = None  # 股价相对 MA20 偏离 %

    # 进阶技术指标
    rsi_6: Optional[float] = None
    rsi_14: Optional[float] = None
    macd_value: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    boll_upper: Optional[float] = None
    boll_mid: Optional[float] = None
    boll_lower: Optional[float] = None

    # K 线数据（精简，最近 60 个交易日）
    klines_daily: List[KLineItem] = Field(default_factory=list)
    klines_weekly: List[KLineItem] = Field(default_factory=list)


class StockDetailResponse(BaseModel):
    """股票详情响应"""
    success: bool
    data: Optional[StockDetail] = None
    message: str = ""
