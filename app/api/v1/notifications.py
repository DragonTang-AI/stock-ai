"""通知中心路由"""
from fastapi import APIRouter, Depends, Query
from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.schemas.notifications import NotificationsPage, NotificationCreate, NotificationItem
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# 内存存储（生产环境应替换为数据库）
_notifications_store: dict[str, list[NotificationItem]] = {}

def _get_user_store(user_id: str) -> list[NotificationItem]:
    if user_id not in _notifications_store:
        _notifications_store[user_id] = []
    return _notifications_store[user_id]

@router.get("/notifications", response_model=NotificationsPage)
async def get_notifications(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    store = _get_user_store(str(current_user.id))
    unread_count = sum(1 for n in store if not n.read)
    items = store[offset:offset + limit]
    return NotificationsPage(
        items=items,
        total=len(store),
        unread_count=unread_count,
        limit=limit,
        offset=offset,
    )

@router.put("/notifications/{notification_id}/read")
async def mark_as_read(notification_id: str, current_user: User = Depends(get_current_user)):
    store = _get_user_store(str(current_user.id))
    for n in store:
        if n.id == notification_id:
            n.read = True
            return {"success": True}
    return {"success": False, "message": "通知不存在"}

@router.put("/notifications/read-all")
async def mark_all_as_read(current_user: User = Depends(get_current_user)):
    store = _get_user_store(str(current_user.id))
    for n in store:
        n.read = True
    return {"success": True, "count": len(store)}

@router.delete("/notifications/{notification_id}")
async def delete_notification(notification_id: str, current_user: User = Depends(get_current_user)):
    store = _get_user_store(str(current_user.id))
    for i, n in enumerate(store):
        if n.id == notification_id:
            store.pop(i)
            return {"success": True}
    return {"success": False, "message": "通知不存在"}

@router.delete("/notifications")
async def clear_all_notifications(current_user: User = Depends(get_current_user)):
    store = _get_user_store(str(current_user.id))
    count = len(store)
    store.clear()
    return {"success": True, "count": count}

@router.post("/notifications")
async def create_notification(body: NotificationCreate, current_user: User = Depends(get_current_user)):
    store = _get_user_store(str(current_user.id))
    item = NotificationItem(
        id=str(uuid.uuid4()),
        type=body.type,
        title=body.title,
        content=body.content,
        created_at=datetime.now().isoformat(),
        read=False,
        data=body.data,
    )
    store.insert(0, item)
    return {"success": True, "data": item}
