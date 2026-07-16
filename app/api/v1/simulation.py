"""app/api/v1/simulation.py — 模拟交易路由，对接真实 trading.place_order"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.schemas.trading import OrderRequest, OrderResponse
from app.services.trading import place_order
from app.core.exceptions import AppException

router = APIRouter()


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
    try:
        req = OrderRequest(
            symbol=symbol,
            side=side,
            quantity=qty,
            price=price if price > 0 else None,
        )
        order = await place_order(db, current_user, req)
        return {"success": True, "data": order, "message": "下单成功"}
    except AppException:
        raise
    except Exception as e:
        raise AppException(code="ORDER_FAILED", message=str(e), status_code=400)
