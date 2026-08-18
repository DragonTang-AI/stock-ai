"""
app/api/v1/internal.py — 内部状态接口（仅限本机回环调用）

供管理后台（8011）跨进程拉取 C 端主服务（8000）的运行时状态：
- AI 托管引擎 HostedEngine 的全局会话快照
- Agent 调度器 scheduler_v2 运行状态
- 今日信号/成交/盈亏聚合（实时口径）

安全：仅接受 127.0.0.1 来源，且要求 X-Internal-Token 匹配。
"""
import os

from fastapi import APIRouter, HTTPException, Request

from app.engine import scheduler_v2
from app.services.hosted_engine import engine as hosted_engine

router = APIRouter()

_INTERNAL_TOKEN = os.getenv("ADMIN_INTERNAL_TOKEN", "stockai_admin_internal_2026")


def _check_internal(request: Request):
    client = request.client.host if request.client else ""
    if client not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=403, detail="forbidden")
    token = request.headers.get("X-Internal-Token", "")
    if token != _INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="forbidden")


@router.get("/hosted/overview")
async def internal_hosted_overview(request: Request):
    """HostedEngine 全局快照 + 调度器状态"""
    _check_internal(request)

    sessions = []
    for uid, s in list(hosted_engine._sessions.items()):
        config = s.get("config", {}) or {}
        sessions.append({
            "user_id": uid,
            "is_active": bool(s.get("is_active")),
            "enabled_at": s.get("enabled_at").isoformat() if s.get("enabled_at") else None,
            "mode": config.get("mode", "AI_HOSTED"),
            "risk_level": config.get("risk_level", "balanced"),
            "scan_count": s.get("scan_count", 0),
            "last_scan": s.get("last_scan"),
            "last_action": s.get("last_action"),
            "total_trades": s.get("total_trades", 0),
            "signals_today": s.get("signals_today", 0),
            "daily_pnl": round(float(s.get("daily_pnl") or 0), 2),
            "daily_pnl_pct": round(float(s.get("daily_pnl_pct") or 0), 2),
            "total_triggered": s.get("total_triggered", 0),
            "total_blocked": s.get("total_blocked", 0),
            "recent_logs": hosted_engine.get_logs(uid, 5),
        })

    active = [s for s in sessions if s["is_active"]]
    return {
        "active_count": len(active),
        "total_sessions": len(sessions),
        "sessions": sessions,
        "scheduler": scheduler_v2.get_status(),
    }
