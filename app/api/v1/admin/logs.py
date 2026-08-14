"""
app/api/v1/admin/logs.py — 后台操作日志查询（异步）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import require_permission
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.operation_log import OperationLog

router = APIRouter()


@router.get("")
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission("logs:view")),
):
    total = (await db.execute(select(func.count()).select_from(OperationLog))).scalar() or 0
    logs = (
        (
            await db.execute(
                select(OperationLog)
                .order_by(OperationLog.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return {
        "total": total,
        "items": [
            {
                "id": l.id,
                "username": l.username,
                "module": l.module,
                "action": l.action,
                "detail": l.detail,
                "ip": l.ip,
                "created_at": l.created_at,
            }
            for l in logs
        ],
    }
