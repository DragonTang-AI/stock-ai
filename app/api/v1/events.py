"""事件埋点路由"""
from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user_optional
from app.schemas.events import BatchPayload, EventResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/events", response_model=EventResponse)
async def report_events(payload: BatchPayload, current_user: User = Depends(get_current_user_optional)):
    """接收批量埋点事件"""
    for evt in payload.events:
        logger.info(f"[tracker] device={payload.device_id} type={evt.event_type} name={evt.event_name} page={evt.page_path} ts={evt.timestamp}")
    return EventResponse(success=True, received=len(payload.events))
