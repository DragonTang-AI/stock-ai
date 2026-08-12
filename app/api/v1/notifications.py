"""app/api/v1/notifications.py — 通知中心路由"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agent import Notification
from app.models.user import User
from app.api.v1.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    content: str
    channel: str
    is_read: bool
    hire_id: int | None = None
    trader_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    total: int
    unread_count: int
    limit: int
    offset: int


@router.get("", response_model=NotificationPage)
async def get_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user.id

    total_q = select(func.count()).select_from(Notification).where(
        Notification.user_id == user_id
    )
    total = (await db.execute(total_q)).scalar() or 0

    unread_q = select(func.count()).select_from(Notification).where(
        Notification.user_id == user_id, Notification.is_read == False
    )
    unread_count = (await db.execute(unread_q)).scalar() or 0

    items_q = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(desc(Notification.created_at))
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(items_q)).scalars().all()

    return NotificationPage(
        items=[NotificationOut.model_validate(r) for r in rows],
        total=total,
        unread_count=unread_count,
        limit=limit,
        offset=offset,
    )


@router.put("/{id}/read")
async def mark_read(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == id, Notification.user_id == current_user.id
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="通知不存在")
    notif.is_read = True
    await db.commit()
    return {"success": True}


@router.put("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        text(
            "UPDATE agent.notifications SET is_read = TRUE "
            "WHERE user_id = :uid AND is_read = FALSE"
        ),
        {"uid": current_user.id},
    )
    await db.commit()
    return {"success": True}


@router.delete("/{id}")
async def delete_notification(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == id, Notification.user_id == current_user.id
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="通知不存在")
    await db.delete(notif)
    await db.commit()
    return {"success": True}


@router.delete("")
async def clear_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        text("DELETE FROM agent.notifications WHERE user_id = :uid"),
        {"uid": current_user.id},
    )
    await db.commit()
    return {"success": True}
