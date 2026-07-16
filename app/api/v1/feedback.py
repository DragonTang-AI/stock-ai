"""app/api/v1/feedback.py — 用户反馈路由（占位桩）"""
from fastapi import APIRouter, Depends
from app.models.user import User
from app.api.v1.auth import get_current_user

router = APIRouter()

@router.post("")
async def submit_feedback(data: dict, current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "反馈已提交"}
