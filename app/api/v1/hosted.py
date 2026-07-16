"""app/api/v1/hosted.py — AI托管路由（占位桩）"""
from fastapi import APIRouter, Depends, Query
from app.models.user import User
from app.api.v1.auth import get_current_user

router = APIRouter()

@router.get("/status")
async def get_hosted_status(current_user: User = Depends(get_current_user)):
    return {
        "mode": "MANUAL", "enabled_at": None, "disabled_at": None,
        "is_active": False, "risk_level": "balanced",
        "max_position_ratio": None, "max_single_trade_ratio": None,
        "min_confidence": None, "single_trade_limit": None,
        "daily_trade_limit": None, "industry_concentration": None,
        "auto_stop_loss": False, "total_trades": 0,
        "total_triggered": 0, "total_blocked": 0,
        "total_skipped": 0, "total_error": 0,
        "active_signals_today": 0, "daily_loss_pct": None,
        "is_audit_mode": False, "disclaimer": "AI托管功能开发中"
    }

@router.post("/switch")
async def switch_hosted(data: dict, current_user: User = Depends(get_current_user)):
    return {"mode": data.get("mode", "MANUAL"), "is_active": False, "disclaimer": "功能开发中"}

@router.patch("/config")
async def update_hosted_config(data: dict, current_user: User = Depends(get_current_user)):
    return {"mode": "AI_HOSTED", "is_active": False, "disclaimer": "功能开发中"}

@router.get("/logs")
async def get_hosted_logs(
    limit: int = Query(50), offset: int = Query(0),
    current_user: User = Depends(get_current_user),
):
    return {"total": 0, "logs": []}

@router.post("/trigger")
async def trigger_hosted(data: dict, current_user: User = Depends(get_current_user)):
    return {"success": False, "data": None, "message": "功能开发中"}
