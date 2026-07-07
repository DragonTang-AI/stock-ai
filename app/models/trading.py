"""
app.models.trading — 交易域模型

5 张表：
- accounts: 用户资金账户（1 用户 1 账户）
- orders: 订单（用户下单）
- trades: 成交记录（订单成交后写入）
- positions: 持仓（每只股票一行，聚合自 trades）
- equity_snapshots: 资产快照（每日收盘后记录）

纸面交易：
- 真实环境无券商对接，所有成交视为立即按市价成交
- 资金初始 100,000 元
- 佣金万 2.5（最低 5 元），卖出印花税千 1
- A 股交易单位 100 股
- T+1：今天买入的股票明天才能卖
"""
from datetime import datetime, date
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ============== 账户 ==============
class Account(Base):
    """用户资金账户（1 用户 1 账户）"""
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    balance: Mapped[float] = mapped_column(Numeric(18, 2), default=100000.0, nullable=False)
    frozen: Mapped[float] = mapped_column(Numeric(18, 2), default=0.0, nullable=False, comment="冻结资金（下单未成交）")
    market: Mapped[str] = mapped_column(String(10), default="A", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", backref="account", uselist=False)


# ============== 订单 ==============
class Order(Base):
    """订单"""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )

    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True, comment="股票代码，如 600519.SH")
    name: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False, comment="buy / sell")
    order_type: Mapped[str] = mapped_column(String(10), default="market", nullable=False, comment="market / limit")
    price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, comment="下单价格（市价单=当前价）")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, comment="数量（股，100 整数倍）")
    filled_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    filled_price: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False, comment="成交均价")
    amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0.0, nullable=False, comment="成交金额")
    commission: Mapped[float] = mapped_column(Numeric(18, 2), default=0.0, nullable=False, comment="佣金")
    tax: Mapped[float] = mapped_column(Numeric(18, 2), default=0.0, nullable=False, comment="印花税（仅卖出）")

    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True,
        comment="pending / filled / partial / canceled / rejected"
    )
    reject_reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_orders_user_status_created", "user_id", "status", "created_at"),
    )


# ============== 成交 ==============
class Trade(Base):
    """成交记录"""
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False, comment="buy / sell")
    price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, comment="成交价")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, comment="成交数量")
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, comment="成交金额")
    commission: Mapped[float] = mapped_column(Numeric(18, 2), default=0.0, nullable=False)
    tax: Mapped[float] = mapped_column(Numeric(18, 2), default=0.0, nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment="成交日期（T+1 判断用）")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_trades_user_date", "user_id", "trade_date"),
        Index("ix_trades_symbol_date", "symbol", "trade_date"),
    )


# ============== 持仓 ==============
class Position(Base):
    """持仓（每只股票一行）"""
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    market: Mapped[str] = mapped_column(String(10), default="A", nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="总持仓")
    available: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="可卖数量（T+1 扣除当日买入）")
    cost_price: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False, comment="加权平均成本价")
    cost_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0.0, nullable=False, comment="总成本")
    market_price: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False, comment="最新市价")
    market_value: Mapped[float] = mapped_column(Numeric(18, 2), default=0.0, nullable=False, comment="市值")
    profit: Mapped[float] = mapped_column(Numeric(18, 2), default=0.0, nullable=False, comment="浮动盈亏")
    profit_pct: Mapped[float] = mapped_column(Numeric(8, 4), default=0.0, nullable=False, comment="盈亏比例 %")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_position_user_symbol"),
        Index("ix_positions_user", "user_id"),
    )


# ============== 资产快照 ==============
class EquitySnapshot(Base):
    """资产快照（每日收盘后记录）"""
    __tablename__ = "equity_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cash: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, comment="现金余额")
    market_value: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, comment="持仓市值")
    total_equity: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, comment="总资产 = 现金 + 市值")
    profit: Mapped[float] = mapped_column(Numeric(18, 2), default=0.0, nullable=False, comment="总盈亏（相对初始 10w）")
    profit_pct: Mapped[float] = mapped_column(Numeric(8, 4), default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "snapshot_date", name="uq_snapshot_user_date"),
    )
