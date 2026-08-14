"""
app/models/operation_log.py — 后台操作审计日志
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OperationLog(Base):
    """后台操作日志表"""

    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    module: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    action: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    detail: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    ip: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
