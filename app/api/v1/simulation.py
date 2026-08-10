"""app.api/v1/simulation.py — 模拟交易路由，对接真实 trading 服务"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.schemas.trading import OrderRequest, OrderResponse
import logging
from app.core.exceptions import AppException
from app.engine.market_hours import is_market_hours, is_hk_market_hours
from app.services.trading import (
    get_account_info,
    get_positions_summary,
    get_orders,
    get_trades,
    place_order,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── 账户 ──

@router.get("/account")
async def simulation_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取模拟账户信息"""
    account_info = await get_account_info(db, current_user)
    return {"success": True, "data": account_info}


# ── 持仓 ──

@router.get("/positions")
async def simulation_positions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取模拟持仓列表"""
    positions, summary = await get_positions_summary(db, current_user)
    return {"success": True, "data": positions, "summary": summary}


# ── 订单历史 ──

@router.get("/orders")
async def simulation_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取模拟订单列表"""
    orders, total = await get_orders(db, current_user)
    return {"success": True, "data": orders, "total": total}


# ── 下单 ──

@router.post("/orders", response_model=OrderResponse)
async def place_simulation_order(
    symbol: str = Query(...),
    side: str = Query(...),
    qty: int = Query(...),
    price: float = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """下单（模拟交易，调用真实 place_order）"""
    from app.services.hosted_engine import engine as hosted_engine
    if hosted_engine.is_active(current_user.id):
        raise AppException(code="HOSTED_ACTIVE", message="AI托管已开启，手动交易已禁用。请先关闭AI托管再操作。", status_code=403)

    is_hk = symbol.upper().endswith('.HK')
    if is_hk:
        if not is_hk_market_hours():
            raise AppException(code="NOT_TRADING_HOURS", message="当前非交易时段（港股：周一至周五 9:30-12:00, 13:00-16:00），无法下单", status_code=400)
    else:
        if not is_market_hours():
            raise AppException(code="NOT_TRADING_HOURS", message="当前非交易时段（A股：周一至周五 9:30-11:30, 13:00-15:00），无法下单", status_code=400)


    try:
        req = OrderRequest(
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price if price > 0 else None,
        )
        order = await place_order(db, current_user, req)
        logger.info(f"Place order: user={current_user.id} symbol={req.symbol} side={req.side.value} qty={req.quantity}")
        return {"success": True, "data": order, "message": "下单成功"}
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Order failed: user={current_user.id} {e}", exc_info=True)
        raise AppException(code="ORDER_FAILED", message=str(e), status_code=400)


# ── 成交记录 ──

@router.get("/trades")
async def simulation_trades(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取模拟成交记录"""
    trades, total = await get_trades(db, current_user)
    return {"success": True, "data": trades, "total": total}
