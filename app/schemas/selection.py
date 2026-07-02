"""
app.schemas.selection — 选股 API 数据模型
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class PickFactor(BaseModel):
    """单个因子的得分明细"""
    name: str = Field(..., description="因子名称：momentum/volume_ratio/trend/turnover")
    value: float = Field(..., description="因子原始值")
    score: float = Field(..., description="因子得分（0~权重×100）")
    weight: float = Field(..., description="因子权重（0~1）")


class StockPick(BaseModel):
    """单只推荐股票"""
    rank: int = Field(..., description="推荐排名（从 1 开始）")
    symbol: str = Field(..., description="股票代码，如 600519.SH")
    name: str = Field(..., description="股票名称")
    price: float = Field(..., description="最新价")
    change_pct: float = Field(..., description="涨跌幅 %")
    volume: int = Field(..., description="成交量（手）")
    turnover_rate: Optional[float] = Field(None, description="换手率 %")
    score: float = Field(..., description="综合评分（0~100）")
    factors: List[PickFactor] = Field(..., description="因子得分明细")
    market: str = Field(..., description="市场：A/HK")


class RecommendRequest(BaseModel):
    """选股推荐请求（GET query 参数）"""
    market: str = Field("all", description="市场过滤：all/A/HK")
    top_n: int = Field(10, ge=1, le=50, description="返回 Top N")
    min_change_pct: float = Field(-2.0, description="最小涨幅 %")
    max_change_pct: float = Field(9.0, description="最大涨幅 %（避开涨停）")


class RecommendResponse(BaseModel):
    """选股推荐响应"""
    success: bool
    picks: List[StockPick] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
