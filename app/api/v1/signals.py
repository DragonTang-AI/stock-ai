"""app/api/v1/signals.py — 信号查询路由"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.user import User
from app.models.signals import Signal
from app.api.v1.auth import get_current_user
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def get_signals(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str = Query(None, description="筛状态: PENDING/TRIGGERED/REJECTED/ERROR"),
    today: bool = Query(False, description="仅今日信号"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的信号列表"""
    conditions = [Signal.user_id == current_user.id]
    
    if today:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        conditions.append(Signal.created_at >= today_start)
    
    if status:
        conditions.append(Signal.status == status)

    count_stmt = select(func.count()).select_from(Signal).where(*conditions)
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Signal)
        .where(*conditions)
        .order_by(desc(Signal.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    signals = result.scalars().all()

    resp = {
        "total": total,
        "signals": [s.to_dict() for s in signals],
    } if not today else {
        "total": total,
        "signals": [s.to_dict() for s in signals],
    }
    return resp
