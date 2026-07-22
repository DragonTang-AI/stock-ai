"""
app/models/broadcast.py — 每日播报模型
"""
import uuid
from datetime import datetime, date

from sqlalchemy import String, Date, Integer, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Broadcast(Base):
    """每日播报表"""

    __tablename__ = "broadcasts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    date: Mapped[date] = mapped_column(Date, unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False, default="每日播报")
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="published"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
