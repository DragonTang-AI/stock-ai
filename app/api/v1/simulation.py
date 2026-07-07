"""app/api/v1/simulation.py — 模拟交易路由（Phase 2 实现）"""
from fastapi import APIRouter, Depends
from app.models.user import User
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.post("/orders")
async def place_order(
    symbol: str,
    side: str,
    qty: int,
    price: float = 0,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    下单（占位，Phase 2 实现）。

    Args:
        symbol: 股票代码
        side: BUY / SELL
        qty: 数量（手）
        price: 价格（0=市价）
    """
    return {
        "success": True,
        "order_id": "placeholder",
        "note": "Phase 2 实现",
    }
