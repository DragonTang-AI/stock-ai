"""用户反馈路由"""
from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(body: FeedbackRequest, current_user: User = Depends(get_current_user)):
    logger.info(f"[feedback] user={current_user.id} category={body.category} page={body.page_path} content={body.content[:100]}")
    return FeedbackResponse(success=True, message="感谢您的反馈！")
