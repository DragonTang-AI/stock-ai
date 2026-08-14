"""app/models/daily_pick.py — 每日推荐股票列表（每日 8:00 预生成，C 端直读）"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DailyPick(Base):
    """每日推荐列表（每日 8:00 服务端定时生成一次）"""

    __tablename__ = "daily_picks"
    __table_args__ = (
        UniqueConstraint("trade_date", "market", "engine", name="uq_daily_picks_date_market_engine"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="交易日期 YYYY-MM-DD")
    market: Mapped[str] = mapped_column(String(8), nullable=False, default="A", comment="市场: A/HK/all")
    picks_json: Mapped[str] = mapped_column(Text, nullable=False, comment="推荐列表 JSON")
    engine: Mapped[str] = mapped_column(String(32), nullable=False, default="factor", comment="生成引擎: factor(因子评分)/committee_llm(LLM委员会)")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduler", comment="生成来源: scheduler/refresh/manual")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ok", comment="状态: ok/running/error")
    error_msg: Mapped[str] = mapped_column(Text, nullable=True, comment="生成失败信息")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
