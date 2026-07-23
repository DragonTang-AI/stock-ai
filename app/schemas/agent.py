"""app/schemas/agent.py — 交易员市场 schema"""
from datetime import datetime, date
from pydantic import BaseModel, Field


class AgentTraderResponse(BaseModel):
    id: str
    code_name: str
    tag: str
    avatar_url: str | None = None
    description: str
    strategy_detail: str | None = None
    masters: str
    hire_price_points: int
    profit_share_pct: float
    annual_return: float | None = None
    max_drawdown: float | None = None
    sharpe_ratio: float | None = None
    win_rate: float | None = None
    total_trades: int | None = None
    radar_scores: dict | None = None
    salary_curve: list | None = None

    class Config:
        from_attributes = True


class AgentTraderDetail(AgentTraderResponse):
    is_hired: bool = False
    management_mode: str | None = None
    hired_at: datetime | None = None
    current_pnl: float | None = None
    recent_performances: list["AgentPerformanceResponse"] = []


class AgentPerformanceResponse(BaseModel):
    period: str
    period_end: date
    return_pct: float
    benchmark_return_pct: float | None = None
    alpha: float | None = None
    max_drawdown: float | None = None
    sharpe_ratio: float | None = None
    win_rate: float | None = None

    class Config:
        from_attributes = True


class AgentPerformanceDetailResponse(BaseModel):
    """交易员表现详情（含收益曲线和雷达图数据）"""
    agent_id: str
    performance_metrics: AgentPerformanceResponse | None = None
    salary_curve: list[dict] = []
    recent_performances: list[AgentPerformanceResponse] = []


class AgentMarketListResponse(BaseModel):
    items: list[AgentTraderResponse]
    total: int


class HireAgentRequest(BaseModel):
    management_mode: str = Field(default="advisory", pattern=r"^(advisory|full_managed)$")


class HireAgentResponse(BaseModel):
    user_agent_id: int
    agent_id: str
    points_spent: int
    balance_after: int
    management_mode: str
    expires_at: datetime | None = None
    message: str = "雇佣成功"


class UserAgentResponse(BaseModel):
    id: int
    agent_id: str
    agent: AgentTraderResponse
    status: str
    management_mode: str
    allocated_capital: float | None = None
    current_pnl: float | None = None
    hired_at: datetime
    expires_at: datetime | None = None

    class Config:
        from_attributes = True


class UpdateManagementModeRequest(BaseModel):
    management_mode: str = Field(pattern=r"^(advisory|full_managed)$")


AgentTraderDetail.model_rebuild()
