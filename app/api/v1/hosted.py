"""app/api/v1/hosted.py — AI托管路由"""
import logging
from datetime import datetime
from typing import Dict
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.models.user import User
from app.api.v1.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# 内存中的托管状态（user_id → config）
_hosted_state: Dict[int, dict] = {}
_hosted_logs: Dict[int, list] = {}

DEFAULT_CONFIG = {
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
}


def _get_state(user_id: int) -> dict:
    """获取用户托管状态，首次访问时初始化"""
    if user_id not in _hosted_state:
        _hosted_state[user_id] = dict(DEFAULT_CONFIG)
    return _hosted_state[user_id]


def _add_log(user_id: int, action: str, detail: str = "", status: str = "info"):
    """记录托管日志"""
    if user_id not in _hosted_logs:
        _hosted_logs[user_id] = []
    _hosted_logs[user_id].insert(0, {
        "id": len(_hosted_logs[user_id]) + 1,
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "detail": detail,
        "status": status,
    })
    # 保留最近 200 条
    if len(_hosted_logs[user_id]) > 200:
        _hosted_logs[user_id] = _hosted_logs[user_id][:200]


@router.get("/status")
async def get_hosted_status(current_user: User = Depends(get_current_user)):
    state = _get_state(current_user.id)
    return {
        "mode": state["mode"],
        "is_active": state["is_active"],
        "risk_level": state["risk_level"],
        "max_position_ratio": state["max_position_ratio"],
        "max_single_trade_ratio": state["max_single_trade_ratio"],
        "min_confidence": state["min_confidence"],
        "single_trade_limit": state["single_trade_limit"],
        "daily_trade_limit": state["daily_trade_limit"],
        "industry_concentration": state["industry_concentration"],
        "auto_stop_loss": state["auto_stop_loss"],
        "enabled_at": state["enabled_at"],
        "disabled_at": state["disabled_at"],
        "total_trades": state.get("total_trades", 0),
        "total_triggered": state.get("total_triggered", 0),
        "total_blocked": state.get("total_blocked", 0),
        "total_skipped": state.get("total_skipped", 0),
        "total_error": state.get("total_error", 0),
        "active_signals_today": 0,
        "daily_loss_pct": None,
        "is_audit_mode": False,
        "disclaimer": "AI托管功能基于技术面量化分析，不构成投资推荐。过往表现不代表未来收益。",
    }


@router.post("/switch")
async def switch_hosted(data: dict, current_user: User = Depends(get_current_user)):
    state = _get_state(current_user.id)
    mode = data.get("mode", state["mode"])
    now = datetime.now().isoformat()

    if mode == "AI_HOSTED":
        state["mode"] = "AI_HOSTED"
        state["is_active"] = True
        state["enabled_at"] = now
        state["disabled_at"] = None
        _add_log(current_user.id, "AI托管已开启", f"模式: {mode}", "success")
        logger.info(f"User {current_user.id}: AI托管已开启")
    else:
        state["mode"] = "MANUAL"
        state["is_active"] = False
        state["disabled_at"] = now
        state["enabled_at"] = state.get("enabled_at")  # 保留开通记录
        _add_log(current_user.id, "AI托管已关闭", f"模式: {mode}", "info")
        logger.info(f"User {current_user.id}: AI托管已关闭")

    return {
        "mode": state["mode"],
        "is_active": state["is_active"],
        "enabled_at": state["enabled_at"],
        "disabled_at": state["disabled_at"],
        "disclaimer": "AI托管功能基于技术面量化分析，不构成投资推荐。",
    }


@router.patch("/config")
async def update_hosted_config(data: dict, current_user: User = Depends(get_current_user)):
    state = _get_state(current_user.id)
    updatable = [
        "risk_level", "max_position_ratio", "max_single_trade_ratio",
        "min_confidence", "single_trade_limit", "daily_trade_limit",
        "industry_concentration", "auto_stop_loss",
    ]
    for key in updatable:
        if key in data:
            state[key] = data[key]
    _add_log(current_user.id, "托管配置已更新", str({k: data[k] for k in updatable if k in data}), "info")

    return {
        "mode": state["mode"],
        "is_active": state["is_active"],
        "risk_level": state["risk_level"],
        "max_position_ratio": state["max_position_ratio"],
        "max_single_trade_ratio": state["max_single_trade_ratio"],
        "min_confidence": state["min_confidence"],
        "single_trade_limit": state["single_trade_limit"],
        "daily_trade_limit": state["daily_trade_limit"],
        "industry_concentration": state["industry_concentration"],
        "auto_stop_loss": state["auto_stop_loss"],
        "disclaimer": "AI托管功能基于技术面量化分析，不构成投资推荐。",
    }


@router.get("/logs")
async def get_hosted_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    logs = _hosted_logs.get(current_user.id, [])
    total = len(logs)
    page = logs[offset:offset + limit]
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": page,
    }


@router.post("/trigger")
async def trigger_hosted(data: dict, current_user: User = Depends(get_current_user)):
    state = _get_state(current_user.id)
    if not state["is_active"]:
        return {
            "success": False,
            "data": None,
            "message": "AI托管未开启，请先开启托管模式",
        }
    # 模拟一次托管扫描
    _add_log(current_user.id, "手动触发扫描", "用户手动触发AI托管扫描", "info")
    return {
        "success": True,
        "data": {
            "scanned_positions": 0,
            "generated_signals": 0,
            "executed_orders": 0,
            "skipped_reasons": [],
        },
        "message": "托管扫描完成，当前无待执行信号",
    }
