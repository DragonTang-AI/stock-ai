"""app/api/v1/notifications.py — 通知中心路由（占位桩）"""
from fastapi import APIRouter, Depends, Query
from app.models.user import User
from app.api.v1.auth import get_current_user

router = APIRouter()

@router.get("")
async def get_notifications(
    limit: int = Query(50), offset: int = Query(0),
    current_user: User = Depends(get_current_user),
):
    return {"success": True, "data": {"items": [], "total": 0, "unread_count": 0, "limit": limit, "offset": offset}}

@router.put("/{id}/read")
async def mark_read(id: str, current_user: User = Depends(get_current_user)):
    return {"success": True}

@router.put("/read-all")
async def mark_all_read(current_user: User = Depends(get_current_user)):
    return {"success": True}

@router.delete("/{id}")
async def delete_notification(id: str, current_user: User = Depends(get_current_user)):
    return {"success": True}

@router.delete("")
async def clear_notifications(current_user: User = Depends(get_current_user)):
    return {"success": True}
