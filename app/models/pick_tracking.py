# -*- coding: utf-8 -*-
"""app/models/pick_tracking.py — 每日推荐逐票追踪（回测闭环数据源）"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PickTracking(Base):
    """每日推荐逐票追踪：记录每次推荐，回测时回填 T+N 收益与基准超额。"""

    __tablename__ = "pick_tracking"
    __table_args__ = (
        UniqueConstraint(
            "trade_date", "market", "engine", "symbol",
            name="uq_pick_tracking_date_market_engine_symbol",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="推荐生成日 YYYY-MM-DD")
    market: Mapped[str] = mapped_column(String(8), nullable=False, default="A", comment="市场: A/HK")
    engine: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="factor/committee_llm")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, comment="股票代码")
    symbol_name: Mapped[str] = mapped_column(String(64), nullable=True, comment="股票名称")
    action: Mapped[str] = mapped_column(String(16), nullable=True, comment="推荐动作")
    confidence: Mapped[int] = mapped_column(Integer, nullable=True, comment="置信度")
    entry_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True, comment="入场价(回测回填)")
    t5_return: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True, comment="T+5 收益率 %")
    t5_benchmark_return: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True, comment="T+5 基准收益率 %(A:沪深300/HK:恒指)")
    t20_return: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True, comment="T+20 收益率 %")
    t20_benchmark_return: Mapped[float] = mapped_column(Numeric(12, 4), nullable=True, comment="T+20 基准收益率 %")
    backtest_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, comment="回测更新时间")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
