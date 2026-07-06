from fastapi import APIRouter, Depends, HTTPException
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


@router.get("/account", response_model=AccountResponse)
async def get_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取账户信息"""
    account_info = await trading_service.get_account_info(db, current_user)
    return {
        "success": True,
        "data": account_info
    }


@router.post("/orders", response_model=OrderResponse)
async def create_order(
    order: OrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建订单"""
    try:
        order_item = await trading_service.place_order(db, current_user, order)
        return {
            "success": True,
            "data": order_item,
            "message": "下单成功"
        }
    except AppException as e:
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
        return {
            "success": True,
            "data": order_item,
            "message": "撤单成功"
        }
    except AppException as e:
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
