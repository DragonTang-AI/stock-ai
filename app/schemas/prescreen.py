"""app/schemas/prescreen.py — Prescreen API Schema"""
from datetime import date
from pydantic import BaseModel, Field


class PrescreenFactorScores(BaseModel):
    momentum: float = Field(ge=0, le=100, description="涨幅动量得分")
    volume_activity: float = Field(ge=0, le=100, description="成交量活跃度百分位")


class PrescreenCandidate(BaseModel):
    rank: int = Field(ge=1)
    symbol: str
    name: str | None = None
    price: float | None = None
    change_pct: float | None = None
    volume: float | None = None
    composite_score: float = Field(ge=0, le=100, description="综合评分")
    factor_scores: PrescreenFactorScores


class PrescreenResponse(BaseModel):
    market: str = Field(description="市场代码: A/HK/US")
    trade_date: str
    pool_size: int = Field(ge=0, description="候选池大小")
    candidates: list[PrescreenCandidate] = Field(description="推荐股票列表")
