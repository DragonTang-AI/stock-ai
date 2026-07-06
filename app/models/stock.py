"""
app.models.stock — 股票收藏域模型

1 张表：
- watchlists: 用户自选股（用户 ID + 股票代码联合唯一）
"""
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Watchlist(Base):
    """自选股表"""
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, comment="股票代码，如 600519.SH")
    note: Mapped[str] = mapped_column(String(100), nullable=True, default=None, comment="备注")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="排序序号")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),
    )

    user = relationship("User", backref="watchlists")
