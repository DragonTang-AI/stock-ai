"""app/api/v1/selection.py — 选股路由（Phase 2 实现）"""
from fastapi import APIRouter, Depends
from app.models.user import User
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("/daily-picks")
async def get_daily_picks(
    current_user: User = Depends(get_current_user),
) -> dict:
    """每日精选（占位，Phase 2 实现）"""
    return {"success": True, "picks": [], "note": "Phase 2 实现"}
