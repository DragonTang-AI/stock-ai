"""
app/api/v1/admin/monitor.py — 系统监控（M5-P0，只读）

服务进程状态（CPU/内存/运行时长）、磁盘/内存资源、调度器状态、操作日志。
"""
import os
import subprocess
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin, require_permission
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.operation_log import OperationLog

router = APIRouter()

PERM = "dashboard:view"

INTERNAL_BASE = os.getenv("ADMIN_INTERNAL_BASE", "http://127.0.0.1:8000")
INTERNAL_TOKEN = os.getenv("ADMIN_INTERNAL_TOKEN", "stockai_admin_internal_2026")


def _run(cmd: str):
    try:
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return (out.stdout or "").strip()
    except Exception:
        return ""


def _proc_info(pattern: str):
    """根据命令行关键字返回进程 PID/CPU/MEM/运行秒数"""
    pid = _run(f"pgrep -f '{pattern}' | head -1")
    if not pid:
        return None
    try:
        pid = pid.splitlines()[0]
        stats = _run(f"ps -p {pid} -o %cpu=,%mem=,etimes=").split()
        return {
            "pid": int(pid),
            "cpu_pct": float(stats[0]) if len(stats) > 0 else 0.0,
            "mem_pct": float(stats[1]) if len(stats) > 1 else 0.0,
            "uptime_sec": int(stats[2]) if len(stats) > 2 else 0,
        }
    except Exception:
        return None


async def _fetch_internal():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                f"{INTERNAL_BASE}/api/v1/internal/hosted/overview",
                headers={"X-Internal-Token": INTERNAL_TOKEN},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return None


@router.get("/overview")
async def monitor_overview(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(PERM)),
):
    # ── 服务进程 ──
    admin_proc = _proc_info("app.admin_main:app")
    stockai_proc = _proc_info("app.main:app")

    # ── 资源 ──
    disk = _run("df -h / | tail -1").split()
    mem = []
    for line in _run("free -m").splitlines():
        if line.startswith("Mem:"):
            mem = line.split()[1:4]
            break
    load = _run("cat /proc/loadavg").split()[:3]

    # ── 数据库 ──
    db_ok = False
    try:
        await db.execute(text("select 1"))
        db_ok = True
    except Exception:
        db_ok = False

    # ── 调度器 ──
    internal = await _fetch_internal()
    scheduler = (internal or {}).get("scheduler") or {}

    # ── 操作日志 ──
    logs = (
        await db.execute(
            select(OperationLog).order_by(desc(OperationLog.created_at)).limit(10)
        )
    ).scalars().all()

    return {
        "generated_at": datetime.now().isoformat(),
        "services": {
            "admin_api": admin_proc or {"online": False},
            "stockai_api": stockai_proc or {"online": False},
            "database": {"online": db_ok},
        },
        "resources": {
            "disk": {
                "total": disk[1] if len(disk) > 1 else None,
                "used": disk[2] if len(disk) > 2 else None,
                "avail": disk[3] if len(disk) > 3 else None,
                "use_pct": disk[4] if len(disk) > 4 else None,
            },
            "memory": {
                "total_mb": int(mem[0]) if len(mem) > 0 else None,
                "used_mb": int(mem[1]) if len(mem) > 1 else None,
                "avail_mb": int(mem[2]) if len(mem) > 2 else None,
            },
            "load_avg": [float(x) for x in load] if load else [],
        },
        "scheduler": {
            "running": bool(scheduler.get("running")),
            "current_phase": scheduler.get("current_phase"),
            "active_hires": scheduler.get("active_hires", 0),
        },
        "recent_logs": [
            {
                "id": l.id,
                "username": l.username,
                "module": l.module,
                "action": l.action,
                "detail": l.detail,
                "ip": l.ip,
                "created_at": l.created_at.isoformat(),
            }
            for l in logs
        ],
    }
