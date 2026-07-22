"""app/api/v1/broadcast.py — 每日播报路由"""
import logging
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.broadcast import Broadcast
from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.services.broadcast import (
    get_today_broadcast,
    get_broadcast_list,
    get_broadcast_by_date,
    get_broadcast_by_id,
    generate_daily_broadcast,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/today")
async def today_endpoint(
    regenerate: bool = Query(False, description="强制重新生成"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取今日播报（不存在则自动生成）"""
    if regenerate:
        try:
            broadcast = await generate_daily_broadcast()
            return _model_to_dict(broadcast)
        except Exception as e:
            logger.error(f"Regenerate broadcast failed: {e}")

    result = await get_today_broadcast(db)
    if result:
        return result

    # 不存在则自动生成一次
    try:
        broadcast = await generate_daily_broadcast()
        return _model_to_dict(broadcast)
    except Exception as e:
        logger.error(f"Auto-generate broadcast failed: {e}")
        return {
            "id": "",
            "date": date.today().isoformat(),
            "title": "今日暂无播报",
            "content": {
                "overview": "今日播报尚未生成，请稍后再试。",
                "recommendations": [],
                "risk_warnings": "市场有风险，投资需谨慎。",
            },
            "audio_url": None,
            "duration": None,
            "created_at": "",
        }


@router.get("/list")
async def list_endpoint(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取历史播报列表（分页）"""
    return await get_broadcast_list(db, limit=limit, offset=offset)


@router.get("/{date_str}")
async def date_endpoint(
    date_str: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """按日期获取播报（YYYY-MM-DD）"""
    result = await get_broadcast_by_date(db, date_str)
    if not result:
        return {
            "id": "",
            "date": date_str,
            "title": "暂无该日播报",
            "content": {"overview": "", "recommendations": [], "risk_warnings": ""},
            "audio_url": None,
            "duration": None,
            "created_at": "",
        }
    return result


@router.get("/audio/{broadcast_id}")
async def audio_endpoint(
    broadcast_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取播报音频 URL"""
    result = await get_broadcast_by_id(db, broadcast_id)
    if not result:
        return {"audio_url": "", "duration": 0}
    return {
        "audio_url": result.get("audio_url") or "",
        "duration": result.get("duration") or 0,
    }


def _model_to_dict(b: Broadcast) -> dict:
    return {
        "id": b.id,
        "date": b.date.isoformat() if b.date else "",
        "title": b.title,
        "content": b.content or {"overview": "", "recommendations": [], "risk_warnings": ""},
        "audio_url": b.audio_url,
        "duration": b.duration,
        "created_at": b.created_at.isoformat() if b.created_at else "",
    }
