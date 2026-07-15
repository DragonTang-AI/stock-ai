"""P1-F3: AI托管 API Schema"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class HostedMode(str, Enum):
    MANUAL = "MANUAL"
    AI_HOSTED = "AI_HOSTED"


class HostedStatusResponse(BaseModel):
    mode: HostedMode
    enabled_at: Optional[datetime] = None
    disabled_at: Optional[datetime] = None
    is_active: bool
    max_position_ratio: Optional[float] = None
    max_single_trade_ratio: Optional[float] = None
    min_confidence: Optional[int] = None
    total_trades: int = 0
    total_triggered: int = 0
    total_blocked: int = 0
    total_skipped: int = 0
    total_error: int = 0
    active_signals_today: int = 0
    daily_loss_pct: Optional[float] = None
    is_audit_mode: bool
    disclaimer: Optional[str] = None


class HostedSwitchRequest(BaseModel):
    mode: HostedMode


class HostedConfigRequest(BaseModel):
    max_position_ratio: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_single_trade_ratio: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_confidence: Optional[int] = Field(None, ge=0, le=100)


class HostedLogItem(BaseModel):
    id: str
    signal_id: Optional[str]
    order_id: Optional[int]
    action: str
    symbol: str
    symbol_name: Optional[str] = None
    target_price: Optional[float]
    qty: Optional[int]
    reason: Optional[str]
    status: str
    error: Optional[str] = None
    created_at: datetime


class HostedLogResponse(BaseModel):
    total: int
    logs: List[HostedLogItem]


class SignalToOrderRequest(BaseModel):
    symbol: str
    signal_id: str
    action: str
    confidence: int
    target_price: float
    reasoning: Optional[str] = None
