"""app/api/v1/broadcast.py — 定时播报路由（占位桩）"""
from fastapi import APIRouter, Depends, Query
from app.models.user import User
from app.api.v1.auth import get_current_user

router = APIRouter()

@router.get("/today")
async def get_today_broadcast(current_user: User = Depends(get_current_user)):
    return {
        "id": "placeholder", "date": "", "created_at": "",
        "title": "播报功能开发中", "content": {"overview": "", "recommendations": [], "risk_warnings": ""},
        "audio_url": None, "duration": None
    }

@router.get("/list")
async def get_broadcast_list(
    limit: int = Query(10), offset: int = Query(0),
    current_user: User = Depends(get_current_user),
):
    return {"items": [], "total": 0, "has_prev": False, "has_next": False}

@router.get("/{date}")
async def get_broadcast_by_date(date: str, current_user: User = Depends(get_current_user)):
    return {"id": "", "date": date, "title": "", "content": {"overview": "", "recommendations": [], "risk_warnings": ""}, "audio_url": None, "duration": None}

@router.get("/audio/{id}")
async def get_broadcast_audio(id: str, current_user: User = Depends(get_current_user)):
    return {"audio_url": "", "duration": 0}
