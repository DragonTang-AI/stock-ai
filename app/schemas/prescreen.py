"""app/schemas/prescreen.py — Prescreen API Schema (对齐 scaffold v2)"""
from datetime import date
from pydantic import BaseModel, Field


class PrescreenFactorScores(BaseModel):
    """因子评分（对接 4-Agent 管线）"""
    momentum: float = Field(ge=0, le=100, description="涨幅动量得分")
    volume_activity: float = Field(ge=0, le=100, description="成交量活跃度百分位")
    trend: float = Field(ge=0, le=100, description="趋势得分（布林带中轨偏离度）")


class PrescreenCandidate(BaseModel):
    """粗筛候选股（对齐 scaffold orchestrator）"""
    rank: int = Field(ge=1)
    market: str = Field(description="市场代码: A/HK")
    symbol: str
    symbol_name: str | None = None
    trade_date: str
    close: str = Field(description="收盘价（字符串，保持精度）")
    composite_score: float = Field(ge=0, le=100, description="综合评分")
    factor_scores: PrescreenFactorScores


class PrescreenResponse(BaseModel):
    """粗筛 API 响应"""
    market: str = Field(description="市场代码: A/HK/US")
    trade_date: str
    pool_size: int = Field(ge=0, description="候选池大小")
    candidates: list[PrescreenCandidate] = Field(description="推荐股票列表")


class DailyPicksResponse(BaseModel):
    """每日精选响应（prescreen 服务层内部使用）"""
    market: str
    trade_date: str
    pool_size: int = Field(ge=0)
    limit: int = Field(ge=1, le=50)
    data_source: str = Field(default="sina_realtime", description="数据来源")
    candidates: list[PrescreenCandidate]


class DailyPicksQuery(BaseModel):
    """每日精选查询参数"""
    market: str
    trade_date: date
    limit: int = Field(default=50, ge=1, le=50)
