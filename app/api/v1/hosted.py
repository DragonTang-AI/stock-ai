"""app.api/v1.hosted.py — AI托管路由

使用 HostedEngine 驱动后台自动交易。
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.services.hosted_engine import engine as hosted_engine

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_CONFIG = {
    "mode": "MANUAL",
    "risk_level": "balanced",
    "max_position_ratio": 80.0,
    "max_single_trade_ratio": 20.0,
    "min_confidence": 60,
    "single_trade_limit": 50000,
    "daily_trade_limit": 200000,
    "industry_concentration": 40.0,
    "auto_stop_loss": True,
    "watchlist": [],
}


@router.get("/status")
async def get_hosted_status(current_user: User = Depends(get_current_user)):
    session = hosted_engine.get_state(current_user.id)
    if session is None:
        return {
            "mode": "MANUAL",
            "is_active": False,
            "risk_level": "balanced",
            "max_position_ratio": 80.0,
            "max_single_trade_ratio": 20.0,
            "min_confidence": 60,
            "single_trade_limit": 50000,
            "daily_trade_limit": 200000,
            "industry_concentration": 40.0,
            "auto_stop_loss": True,
            "enabled_at": None,
            "disabled_at": None,
            "total_trades": 0,
            "scan_count": 0,
            "last_scan": None,
            "last_action": None,
            "active_signals_today": 0,
            "daily_loss_pct": None,
            "is_audit_mode": False,
            "disclaimer": "AI托管功能基于技术面量化分析，不构成投资推荐。过往表现不代表未来收益。",
        }

    config = session.get("config", {})
    return {
        "mode": "AI_HOSTED",
        "is_active": session["is_active"],
        "risk_level": config.get("risk_level", "balanced"),
        "max_position_ratio": config.get("max_position_ratio", 80.0),
        "max_single_trade_ratio": config.get("max_single_trade_ratio", 20.0),
        "min_confidence": config.get("min_confidence", 60),
        "single_trade_limit": config.get("single_trade_limit", 50000),
        "daily_trade_limit": config.get("daily_trade_limit", 200000),
        "industry_concentration": config.get("industry_concentration", 40.0),
        "auto_stop_loss": config.get("auto_stop_loss", True),
        "enabled_at": session["enabled_at"].isoformat() if session.get("enabled_at") else None,
        "disabled_at": None,
        "total_trades": session.get("total_trades", 0),
        "scan_count": session.get("scan_count", 0),
        "last_scan": session.get("last_scan"),
        "last_action": session.get("last_action"),
        "active_signals_today": 0,
        "daily_loss_pct": None,
        "is_audit_mode": False,
        "disclaimer": "AI托管功能基于技术面量化分析，不构成投资推荐。过往表现不代表未来收益。",
    }


@router.post("/switch")
async def switch_hosted(data: dict, current_user: User = Depends(get_current_user)):
    mode = data.get("mode", "MANUAL")

    if mode == "AI_HOSTED":
        config = {
            "risk_level": data.get("risk_level", "balanced"),
            "max_position_ratio": data.get("max_position_ratio", 80.0),
            "max_single_trade_ratio": data.get("max_single_trade_ratio", 20.0),
            "min_confidence": data.get("min_confidence", 60),
            "single_trade_limit": data.get("single_trade_limit", 50000),
            "daily_trade_limit": data.get("daily_trade_limit", 200000),
            "industry_concentration": data.get("industry_concentration", 40.0),
            "auto_stop_loss": data.get("auto_stop_loss", True),
            "watchlist": data.get("watchlist", []),
        }
        session = await hosted_engine.enable(current_user.id, config)
        return {
            "mode": "AI_HOSTED",
            "is_active": session["is_active"],
            "enabled_at": session["enabled_at"].isoformat(),
            "disabled_at": None,
            "disclaimer": "AI托管功能基于技术面量化分析，不构成投资推荐。",
        }
    else:
        result = await hosted_engine.disable(current_user.id)
        return {
            "mode": "MANUAL",
            "is_active": False,
            "enabled_at": None,
            "disabled_at": datetime.now().isoformat(),
            "disclaimer": "AI托管功能基于技术面量化分析，不构成投资推荐。",
        }


@router.patch("/config")
async def update_hosted_config(data: dict, current_user: User = Depends(get_current_user)):
    session = hosted_engine.get_state(current_user.id)
    if session is None:
        return {
            "success": False,
            "message": "AI托管未开启，请先开启托管模式",
        }

    updatable = [
        "risk_level", "max_position_ratio", "max_single_trade_ratio",
        "min_confidence", "single_trade_limit", "daily_trade_limit",
        "industry_concentration", "auto_stop_loss", "watchlist",
    ]
    updates = {k: data[k] for k in updatable if k in data}
    result = await hosted_engine.update_config(current_user.id, updates)

    config = result.get("config", {})
    return {
        "mode": "AI_HOSTED",
        "is_active": result["is_active"],
        "risk_level": config.get("risk_level", "balanced"),
        "max_position_ratio": config.get("max_position_ratio", 80.0),
        "max_single_trade_ratio": config.get("max_single_trade_ratio", 20.0),
        "min_confidence": config.get("min_confidence", 60),
        "single_trade_limit": config.get("single_trade_limit", 50000),
        "daily_trade_limit": config.get("daily_trade_limit", 200000),
        "industry_concentration": config.get("industry_concentration", 40.0),
        "auto_stop_loss": config.get("auto_stop_loss", True),
        "disclaimer": "AI托管功能基于技术面量化分析，不构成投资推荐。",
    }


@router.get("/logs")
async def get_hosted_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    logs = hosted_engine.get_logs(current_user.id)
    total = len(logs)
    formatted = []
    for i, entry in enumerate(reversed(logs)):
        formatted.append({
            "id": total - i,
            "timestamp": entry["time"],
            "action": entry["message"],
            "detail": "",
            "status": entry["level"],
        })
    page = formatted[offset:offset + limit]
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": page,
    }


@router.post("/trigger")
async def trigger_hosted(data: dict, current_user: User = Depends(get_current_user)):
    if not hosted_engine.is_active(current_user.id):
        return {
            "success": False,
            "data": None,
            "message": "AI托管未开启，请先开启托管模式",
        }
    return {
        "success": True,
        "data": {
            "scanned_positions": 0,
            "generated_signals": 0,
            "executed_orders": 0,
        },
        "message": "托管引擎正在后台自动运行，每分钟扫描一次",
    }
