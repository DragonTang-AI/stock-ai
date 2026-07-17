"""性能监控路由"""
from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user_optional
from app.schemas.metrics import MetricsPayload, MetricsResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/metrics", response_model=MetricsResponse)
async def report_metrics(payload: MetricsPayload, current_user: User = Depends(get_current_user_optional)):
    for entry in payload.entries:
        logger.debug(f"[metrics] device={payload.device_id} name={entry.name} value={entry.value}{entry.unit} page={entry.page}")
    return MetricsResponse(success=True, received=len(payload.entries))
