"""
app/api/v1/portfolio.py — 持仓路由（Phase 2 实现）
"""
from fastapi import APIRouter, Depends
from app.models.user import User
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("/positions")
async def get_positions(
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取当前持仓（占位，Phase 2 实现）"""
    return {
        "success": True,
        "positions": [],
        "total_value": 0.0,
        "total_profit": 0.0,
        "note": "Phase 2 实现",
    }


@router.get("/account")
async def get_account(
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取账户信息（占位，Phase 2 实现）"""
    return {
        "success": True,
        "account_id": 0,
        "balance": 100000.0,
        "market": "A",
        "note": "Phase 2 实现",
    }
