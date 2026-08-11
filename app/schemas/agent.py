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
    config_source: str = "default"

    class Config:
        from_attributes = True


class UpdateManagementModeRequest(BaseModel):
    management_mode: str = Field(pattern=r"^(advisory|full_managed)$")


# ── 控制台 Schemas ──

class ConsoleOverviewResponse(BaseModel):
    hire_id: int
    trader_name: str
    trader_tag: str = ""
    management_mode: str
    status: str
    total_assets: float = 0
    unrealized_pnl: float = 0
    today_signals: int = 0
    pending_signals: int = 0
    position_count: int = 0


class ConsoleSignalResponse(BaseModel):
    id: int
    hire_id: int
    trader_id: str
    symbol: str
    symbol_name: str
    market: str
    action: str
    price: float
    quantity: int
    confidence: int
    reasoning: str | None = None
    exec_status: str
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class SignalConfirmRequest(BaseModel):
    quantity: int | None = None


class ConsolePortfolioResponse(BaseModel):
    id: int
    hire_id: int
    symbol: str
    symbol_name: str
    quantity: int
    avg_cost: float
    current_price: float | None = None
    market_value: float | None = None
    unrealized_pnl: float | None = None

    class Config:
        from_attributes = True


class ConsoleTradeResponse(BaseModel):
    id: int
    symbol: str
    symbol_name: str
    action: str
    price: float
    quantity: int
    confidence: int
    reasoning: str | None = None
    exec_status: str
    executed_at: datetime | None = None


class EquityCurvePoint(BaseModel):
    date: str
    equity: float
    daily_pnl: float = 0


AgentTraderDetail.model_rebuild()


# ── Agent 配置 Schemas ──

class AgentConfigRequest(BaseModel):
    """配置请求（所有字段均可选，只传要修改的）"""
    markets: list[str] | None = None
    trade_hours_pref: str | None = None
    dormant_off_hours: bool | None = None
    sectors: list[str] | None = None
    market_cap_min: float | None = None
    market_cap_max: float | None = None
    min_avg_amount: float | None = None
    exclude_st: bool | None = None
    exclude_new_listing_days: int | None = None
    exclude_limit_near: bool | None = None
    allocated_capital: float | None = None
    max_order_pct: float | None = None
    max_position_pct: float | None = None
    max_position_count: int | None = None
    trading_style: str | None = None
    signal_interval_min: int | None = None
    daily_max_signals: int | None = None
    daily_max_executions: int | None = None
    daily_max_amount_pct: float | None = None
    loss_stop_pct: float | None = None
    loss_stop_amount: float | None = None
    risk_trigger_action: str | None = None
    risk_enabled: bool | None = None
    t1_enabled: bool | None = None
    auto_exec_confidence: int | None = None
    max_auto_exec_per_round: int | None = None
    analyze_ticker_limit: int | None = None
    auto_exec_enabled: bool | None = None
    notify_channels: list[str] | None = None


class AgentConfigResponse(BaseModel):
    """配置响应"""
    hire_id: int
    markets: list[str]
    trade_hours_pref: str
    dormant_off_hours: bool
    sectors: list[str]
    market_cap_min: float | None = None
    market_cap_max: float | None = None
    min_avg_amount: float
    exclude_st: bool
    exclude_new_listing_days: int
    exclude_limit_near: bool
    allocated_capital: float
    max_order_pct: float
    max_position_pct: float
    max_position_count: int
    trading_style: str
    signal_interval_min: int
    daily_max_signals: int
    daily_max_executions: int
    daily_max_amount_pct: float
    loss_stop_pct: float
    loss_stop_amount: float | None = None
    risk_trigger_action: str
    risk_enabled: bool
    t1_enabled: bool
    auto_exec_confidence: int
    max_auto_exec_per_round: int
    analyze_ticker_limit: int = 10
    auto_exec_enabled: bool = True
    notify_channels: list[str]
    config_source: str = "default"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ActivateAgentResponse(BaseModel):
    """启用交易员响应"""
    user_agent_id: int
    status: str
    message: str


class DeactivateAgentResponse(BaseModel):
    """停用交易员响应"""
    user_agent_id: int
    status: str
    message: str
