"""app/schemas/points.py — 积分相关 schema"""
from datetime import datetime
from pydantic import BaseModel, Field


class PointsBalanceResponse(BaseModel):
    balance: int
    total_earned: int
    total_spent: int
    updated_at: datetime | None = None


class PointsTransactionResponse(BaseModel):
    id: int
    amount: int
    balance_after: int
    tx_type: str
    reference_id: str | None = None
    description: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class PointsHistoryResponse(BaseModel):
    items: list[PointsTransactionResponse]
    total: int


class DailyCheckinResponse(BaseModel):
    success: bool
    points_earned: int
    balance: int
    consecutive_days: int
