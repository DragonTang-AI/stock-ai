"""app/api/v1/feedback.py — 用户反馈路由（占位桩）"""
import logging
from fastapi import APIRouter, Depends
from app.models.user import User
from app.api.v1.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("")
async def submit_feedback(data: dict, current_user: User = Depends(get_current_user)):
    logger.info(f"收到用户反馈 user_id={current_user.id} content={str(data)[:200]}")
    return {"success": True, "message": "反馈已提交"}
