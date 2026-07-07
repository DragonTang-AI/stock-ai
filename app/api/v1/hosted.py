"""P1-F3: AI托管 API 路由"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.schemas.hosted import (
    HostedStatusResponse,
    HostedSwitchRequest,
    HostedConfigRequest,
    HostedLogResponse,
    SignalToOrderRequest,
    HostedMode,
)
from app.services import hosted as hosted_service

router = APIRouter(tags=["AI托管"])


@router.get("/status", response_model=HostedStatusResponse)
async def get_hosted_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前 AI 托管状态"""
    return await hosted_service.get_hosted_status(db, current_user)


@router.post("/switch", response_model=HostedStatusResponse)
async def switch_hosted_mode(
    req: HostedSwitchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    开启 / 关闭 AI 托管
    
    开启后系统将根据 4-Agent 选股信号自动执行纸面交易。
    所有交易受风控保护（仓位上限 / 日亏熔断 / 置信度阈值）。
    审核模式（IS_AUDIT_MODE=True）下仅记录，不实际执行。
    """
    return await hosted_service.switch_hosted_mode(db, current_user, req.mode)


@router.patch("/config", response_model=HostedStatusResponse)
async def update_hosted_config(
    req: HostedConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新 AI 托管风控参数（需先开启托管）
    
    - max_position_ratio: 单票仓位上限（默认 15%）
    - max_single_trade_ratio: 单笔交易上限（默认 5%）
    - min_confidence: 最低执行置信度（默认 60）
    """
    settings = await hosted_service._get_hosted_settings(db, current_user.id)
    if not settings or settings.get("mode") != "AI_HOSTED":
        raise AppException("请先开启 AI 托管模式", status_code=400)
    return await hosted_service.switch_hosted_mode(
        db, current_user, HostedMode.AI_HOSTED, config=req
    )


@router.get("/logs", response_model=HostedLogResponse)
async def get_hosted_logs(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取 AI 托管执行历史"""
    total, logs = await hosted_service.get_hosted_logs(db, current_user, limit)
    return HostedLogResponse(total=total, logs=logs)


@router.post("/trigger", response_model=dict)
async def trigger_signal_order(
    req: SignalToOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    手动触发信号 → 纸面订单（通常由后台任务调用）
    
    在 AI 托管开启状态下，提交信号触发下单。
    会经过完整风控检查（仓位 / 余额 / 置信度）。
    """
    result = await hosted_service.trigger_signal_order(
        db,
        current_user,
        req.symbol,
        req.signal_id,
        req.action,
        req.confidence,
        req.target_price,
        req.reasoning,
    )
    return {"success": True, "data": result}
