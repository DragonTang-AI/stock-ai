"""
app.models.kline — K 线日线数据 ORM 模型

对应生产表：market.kline_daily
（P1-F4 新增唯一约束 + 索引，详见 migrations/versions/p1f4_kline_unique.py）
"""
from sqlalchemy import (
    Numeric,
    String,
    Integer,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DailyKline(Base):
    """日线 K 线数据（market.kline_daily）"""

    __tablename__ = "kline_daily"
    __table_args__ = (
        UniqueConstraint(
            "symbol", "trade_date", "market",
            name="uk_kline_symbol_date_market",
        ),
        Index("ix_kline_symbol_date", "symbol", "trade_date"),
        {"schema": "market"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    market: Mapped[str] = mapped_column(String(8), nullable=False, default="A")
    open: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(20, 2), nullable=True)
