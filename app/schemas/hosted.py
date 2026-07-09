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
    is_active: bool  # 当前是否处于托管状态

    # 风控参数（null=用全局默认值）
    max_position_ratio: Optional[float] = None
    max_single_trade_ratio: Optional[float] = None
    min_confidence: Optional[int] = None

    # 实时统计
    total_trades: int = 0
    total_triggered: int = 0    # 执行成功
    total_blocked: int = 0      # 风控拦截
    total_skipped: int = 0      # 重复跳过
    total_error: int = 0        # 执行异常
    active_signals_today: int = 0
    daily_loss_pct: Optional[float] = None

    # 合规提示
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
    symbol_name: Optional[str] = None  # 股票名称（从行情服务获取）
    target_price: Optional[float]
    qty: Optional[int]
    reason: Optional[str]
    status: str  # TRIGGERED | BLOCKED | SKIPPED | ERROR
    error: Optional[str] = None
    created_at: datetime


class HostedLogResponse(BaseModel):
    total: int
    logs: List[HostedLogItem]


class SignalToOrderRequest(BaseModel):
    """手动触发信号→订单转换（调试用）"""
    symbol: str
    signal_id: str
    action: str
    confidence: int
    target_price: float
    reasoning: Optional[str] = None
