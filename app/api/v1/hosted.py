"""AI托管 API 路由"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.schemas.hosted import (
    HostedMode, HostedStatusResponse, HostedSwitchRequest, HostedConfigRequest,
    HostedLogResponse, SignalToOrderRequest,
)
from app.services import hosted as hosted_service

router = APIRouter()


@router.get("/status", response_model=HostedStatusResponse)
async def get_status(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """获取 AI 托管状态"""
    return await hosted_service.get_hosted_status(db, current_user)


@router.post("/switch", response_model=HostedStatusResponse)
async def switch_mode(
    req: HostedSwitchRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """开关 AI 托管模式"""
    return await hosted_service.switch_hosted_mode(db, current_user, req.mode)


@router.patch("/config", response_model=HostedStatusResponse)
async def update_config(
    req: HostedConfigRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """更新风控配置（保持当前模式不变）"""
    status = await hosted_service.get_hosted_status(db, current_user)
    return await hosted_service.switch_hosted_mode(db, current_user, status.mode, req)


@router.get("/logs", response_model=HostedLogResponse)
async def get_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """获取 AI 托管交易日志"""
    return await hosted_service.get_hosted_logs(
        db, current_user.id, limit=limit, offset=offset
    )


@router.post("/trigger")
async def trigger_order(
    req: SignalToOrderRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db),
):
    """手动触发信号下单"""
    result = await hosted_service.trigger_signal_order(
        db, current_user,
        symbol=req.symbol,
        signal_id=req.signal_id,
        action=req.action,
        confidence=req.confidence,
        target_price=req.target_price,
        reasoning=req.reasoning,
    )
    return result
