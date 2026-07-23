"""app/models/agent.py — 交易员市场模型"""
from datetime import datetime, date

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, func,
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
