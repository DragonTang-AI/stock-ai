import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.core.exceptions import AppException
from app.models.user import User
from app.schemas.trading import (
    AccountResponse,
    OrderResponse, OrderRequest, OrderListResponse,
    TradeListResponse,
    PositionListResponse
)
from app.services import trading as trading_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/account", response_model=AccountResponse)
async def get_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    market: str = Query("A", description="市场：A / HK"),
):
    """获取账户信息"""
    account_info = await trading_service.get_account_info(db, current_user, market)
    return {
        "success": True,
        "data": account_info
    }


@router.post("/account/init-hk")
async def init_hk_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """初始化港股模拟账户（10 万 HKD 初始资金）"""
    from app.models.trading import Account
    from decimal import Decimal
    stmt = select(Account).where(Account.user_id == current_user.id, Account.market == "HK")
    result = await db.execute(stmt)
    hk_account = result.scalar_one_or_none()
    if hk_account:
        return {"success": True, "data": {"message": "港股账户已存在", "account_id": hk_account.id, "balance": float(hk_account.balance)}}
    hk_account = Account(
        user_id=current_user.id,
        balance=Decimal("100000.00"),
        frozen=Decimal("0"),
        market="HK",
        total_deposited=Decimal("100000.00"),
    )
    db.add(hk_account)
    await db.commit()
    await db.refresh(hk_account)
    return {"success": True, "data": {"message": "港股账户创建成功", "account_id": hk_account.id, "balance": 100000.00}}

@router.post("/orders", response_model=OrderResponse)
async def create_order(
    order: OrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建订单"""
    # AI托管开启时禁止手动下单
    from app.services.hosted_engine import engine as hosted_engine
    if hosted_engine.is_active(current_user.id):
        raise AppException(code="HOSTED_ACTIVE", message="AI托管已开启，手动交易已禁用。请先关闭AI托管再操作。", status_code=403)
    
    try:
        order_item = await trading_service.place_order(db, current_user, order)
        logger.info(f"下单成功 user_id={current_user.id} symbol={order.symbol} side={order.side} qty={order.quantity} order_id={getattr(order_item, 'id', None)}")
        return {
            "success": True,
            "data": order_item,
            "message": "下单成功"
        }
    except AppException as e:
        logger.warning(f"下单失败 user_id={current_user.id} symbol={order.symbol} side={order.side} qty={order.quantity} error={e.message}")
        return {
            "success": False,
            "data": None,
            "message": e.message
        }


@router.get("/orders", response_model=OrderListResponse)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取订单列表"""
    orders, total = await trading_service.get_orders(db, current_user)
    return {
        "success": True,
        "data": orders,
        "total": len(orders)
    }


@router.delete("/orders/{order_id}", response_model=OrderResponse)
async def cancel_order_endpoint(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """撤单"""
    try:
        order_item = await trading_service.cancel_order(db, current_user, order_id)
        logger.info(f"撤单成功 user_id={current_user.id} order_id={order_id}")
        return {
            "success": True,
            "data": order_item,
            "message": "撤单成功"
        }
    except AppException as e:
        logger.warning(f"撤单失败 user_id={current_user.id} order_id={order_id} error={e.message}")
        return {
            "success": False,
            "data": None,
            "message": e.message
        }


@router.get("/trades", response_model=TradeListResponse)
async def list_trades(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取成交列表"""
    trades = await trading_service.get_trades(db, current_user)
    return {
        "success": True,
        "data": trades,
        "total": len(trades)
    }


@router.get("/positions", response_model=PositionListResponse)
async def list_positions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取持仓列表"""
    positions, summary = await trading_service.get_positions_summary(db, current_user)
    return {
        "success": True,
        "data": positions,
        "summary": summary
    }
