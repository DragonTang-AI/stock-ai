"""app/api/v1/analysis.py — 分析路由（Phase 2 实现）"""
from fastapi import APIRouter, Depends
from app.models.user import User
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("/diagnose/{symbol}")
async def diagnose_position(
    symbol: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """持仓诊断（占位，Phase 2 实现）"""
    return {"success": True, "symbol": symbol, "note": "Phase 2 实现"}
