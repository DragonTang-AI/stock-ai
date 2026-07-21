"""app/models/signals.py — 信号持久化模型"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Signal(Base):
    __tablename__ = "signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    signal_id = Column(String(100), unique=True, nullable=False)
    action = Column(String(10), nullable=False)
    symbol = Column(String(20), nullable=False)
    symbol_name = Column(String(100), nullable=True)
    target_price = Column(Float, nullable=True)
    qty = Column(Integer, nullable=True)
    confidence = Column(Integer, nullable=True)
    reason = Column(Text, nullable=True)
    reason_codes = Column(JSON, default=list)
    status = Column(String(10), nullable=False, default="PENDING")
    order_id = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "signal_id": self.signal_id,
            "action": self.action,
            "symbol": self.symbol,
            "symbol_name": self.symbol_name,
            "target_price": self.target_price,
            "qty": self.qty,
            "confidence": self.confidence,
            "reason": self.reason,
            "reason_codes": self.reason_codes or [],
            "status": self.status,
            "order_id": self.order_id,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
