"""
app/api/v1/simulation.py — 模拟交易路由（Phase 2 真实撮合）
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.api.v1.auth import get_current_user
from app.schemas.trading import OrderRequest
from app.services.trading import place_order
from app.core.database import get_db

router = APIRouter()


def _normalize_symbol(symbol: str) -> str:
    """
    将新浪格式符号转为标准格式，再做 .upper()。

    转换规则：
      sh600519 → 600519.SH
      sz000001 → 000001.SZ
      bj888888 → 888888.BJ
      600519.SH → 600519.SH (直接返回)
    """
    s = symbol.strip()
    if s.startswith("sh"):
        return f"{s[2:]}.SH"
    elif s.startswith("sz"):
        return f"{s[2:]}.SZ"
    elif s.startswith("bj"):
        return f"{s[2:]}.BJ"
    else:
        # 已是标准格式（如 600519.SH）或直接返回
        return s.upper()


@router.post("/orders")
async def simulate_place_order(
    symbol: str,
    side: str,
    qty: int,
    price: float = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    模拟下单（真实纸面撮合）

    Args:
        symbol: 股票代码，支持 sh600519 / 600519.SH 等多种格式
        side:   buy / sell
        qty:    数量（股，100 整数倍）
        price:  限价（不传=市价）
    """
    normalized = _normalize_symbol(symbol)
    req = OrderRequest(
        symbol=normalized,
        side=side.lower(),
        order_type="limit" if price > 0 else "market",
        quantity=qty,
        price=price,
    )
    try:
        order_item = await place_order(db, current_user, req)
        return {
            "success": True,
            "order_id": order_item.id,
            "symbol": order_item.symbol,
            "name": order_item.name,
            "side": order_item.side,
            "order_type": order_item.order_type,
            "price": order_item.price,
            "quantity": order_item.quantity,
            "filled_price": order_item.filled_price,
            "filled_quantity": order_item.filled_quantity,
            "amount": order_item.amount,
            "commission": order_item.commission,
            "tax": order_item.tax,
            "status": order_item.status,
            "created_at": str(order_item.created_at),
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "order_id": None,
        }
