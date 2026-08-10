"""app/models/agent.py — 交易员市场模型"""
from datetime import datetime, date

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, func, Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentTrader(Base):
    __tablename__ = "agent_traders"
    __table_args__ = {"schema": "agent"}

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    code_name: Mapped[str] = mapped_column(String(32), nullable=False)
    tag: Mapped[str] = mapped_column(String(32), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    strategy_detail: Mapped[str | None] = mapped_column(String, nullable=True)
    masters: Mapped[str] = mapped_column(String(256), nullable=False)
    hire_price_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    profit_share_pct: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    annual_return: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    sharpe_ratio: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    win_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    total_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    radar_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    salary_curve: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UserAgent(Base):
    __tablename__ = "user_agents"
    __table_args__ = {"schema": "agent"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("agent.agent_traders.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    management_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="advisory")
    allocated_capital: Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)
    current_pnl: Mapped[float] = mapped_column(Numeric(16, 2), nullable=True, default=0)
    hired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AgentPerformance(Base):
    __tablename__ = "agent_performances"
    __table_args__ = {"schema": "agent"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("agent.agent_traders.id", ondelete="CASCADE"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(16), nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    return_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    benchmark_return_pct: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    alpha: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    sharpe_ratio: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    win_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AgentSignal(Base):
    """交易信号"""
    __tablename__ = "agent_signals"
    __table_args__ = {"schema": "agent"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hire_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agent.user_agents.id", ondelete="CASCADE"), nullable=False
    )
    trader_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("agent.agent_traders.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    symbol_name: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(4), nullable=False, default="A")  # A / HK
    action: Mapped[str] = mapped_column(String(8), nullable=False)  # buy / sell
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    exec_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AgentPortfolio(Base):
    """交易员持仓"""
    __tablename__ = "agent_portfolios"
    __table_args__ = {"schema": "agent"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hire_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agent.user_agents.id", ondelete="CASCADE"), nullable=False
    )
    trader_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("agent.agent_traders.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    symbol_name: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    current_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    market_value: Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)
    unrealized_pnl: Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class AgentConfig(Base):
    """交易员配置（P0: 参数化支撑）"""
    __tablename__ = "agent_configs"
    __table_args__ = {"schema": "agent"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hire_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agent.user_agents.id", ondelete="CASCADE"), nullable=False
    )
    markets: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: ["A股"])
    trade_hours_pref: Mapped[str] = mapped_column(String(16), nullable=False, default="follow_market")
    dormant_off_hours: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sectors: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    market_cap_min: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    market_cap_max: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    min_avg_amount: Mapped[float] = mapped_column(Numeric, nullable=False, default=5000)
    exclude_st: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    exclude_new_listing_days: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    exclude_limit_near: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allocated_capital: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=100000)
    max_order_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=20)
    max_position_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=30)
    max_position_count: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    trading_style: Mapped[str] = mapped_column(String(16), nullable=False, default="steady")
    signal_interval_min: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    daily_max_signals: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    daily_max_executions: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    daily_max_amount_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=30)
    loss_stop_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=5)
    loss_stop_amount: Mapped[float | None] = mapped_column(Numeric(16, 2), nullable=True)
    risk_trigger_action: Mapped[str] = mapped_column(String(16), nullable=False, default="dormant")
    risk_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    t1_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_exec_confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=70)
    max_auto_exec_per_round: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    notify_channels: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: ["inbox"])
    config_source: Mapped[str] = mapped_column(String(16), nullable=False, default="default")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
