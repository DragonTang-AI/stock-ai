"""app/api/v1/signals.py — 信号日志路由（占位桩）"""
from fastapi import APIRouter, Depends, Query
from app.models.user import User
from app.api.v1.auth import get_current_user

router = APIRouter()

@router.get("")
async def get_signals(
    limit: int = Query(50), offset: int = Query(0),
    current_user: User = Depends(get_current_user),
):
    return {"total": 0, "signals": []}
