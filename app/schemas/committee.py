"""app/schemas/committee.py — 4-Agent 选股委员会响应 Schema"""
from pydantic import BaseModel, Field

from app.schemas.signals import Signal


class CommitteeRunResponse(BaseModel):
    """4-Agent 选股委员会执行结果"""
    market: str = Field(description="市场代码: A/HK")
    trade_date: str = Field(description="交易日期 YYYY-MM-DD")
    candidate_pool_size: int = Field(ge=0, description="原始候选池大小")
    candidates_evaluated: int = Field(ge=0, description="实际参与评分的候选股数量")
    signal_limit: int = Field(description="本次输出信号上限")
    pipeline: str = Field(
        default="langgraph_committee_v1",
        description="管线版本标识",
    )
    signals: list[Signal] = Field(description="输出信号列表（按置信分降序）")
