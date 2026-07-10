"""
app/api/v1/broadcast.py — 每日播报端点

前端 /broadcast 页面接口：
- GET /broadcast/today      今日播报
- GET /broadcast/list       历史播报分页列表
- GET /broadcast/{date}     指定日期播报
- GET /broadcast/audio/{id} 播报音频 URL
"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/today")
async def get_today_broadcast(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取今日播报"""
    today = date.today().isoformat()
    row = await db.execute(
        text(
            "SELECT id, date, title, content, audio_url, duration, created_at "
            "FROM public.broadcasts WHERE date = :today "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"today": today},
    )
    r = row.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="今日播报尚未生成")
    return _format_broadcast(r)


@router.get("/list")
async def get_broadcast_list(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    """获取历史播报列表（分页）"""
    # 总数
    total_row = await db.execute(text("SELECT count(*) FROM public.broadcasts"))
    total = total_row.scalar()

    rows = await db.execute(
        text(
            "SELECT id, date, title, content, audio_url, duration, created_at "
            "FROM public.broadcasts ORDER BY date DESC "
            "LIMIT :limit OFFSET :offset"
        ),
        {"limit": limit, "offset": offset},
    )
    items = [_format_broadcast(r) for r in rows.fetchall()]

    return {
        "items": items,
        "total": total,
        "has_prev": offset > 0,
        "has_next": offset + limit < total,
    }


@router.get("/{target_date}")
async def get_broadcast_by_date(
    target_date: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取指定日期的播报（格式 YYYY-MM-DD）"""
    try:
        date.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    row = await db.execute(
        text(
            "SELECT id, date, title, content, audio_url, duration, created_at "
            "FROM public.broadcasts WHERE date = :d LIMIT 1"
        ),
        {"d": target_date},
    )
    r = row.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail=f"未找到 {target_date} 的播报")
    return _format_broadcast(r)


@router.get("/audio/{broadcast_id}")
async def get_broadcast_audio(
    broadcast_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取播报音频 URL"""
    row = await db.execute(
        text("SELECT audio_url, duration FROM public.broadcasts WHERE id = :id"),
        {"id": broadcast_id},
    )
    r = row.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="播报不存在")

    return {
        "audio_url": r[0],
        "duration": r[1],
    }


def _format_broadcast(row):
    """将数据库行格式化为前端期望的 JSON"""
    return {
        "id": str(row[0]),
        "date": row[1].isoformat() if isinstance(row[1], date) else row[1],
        "created_at": (row[6].isoformat() if isinstance(row[6], datetime) else row[6]) if row[6] else None,
        "title": row[2],
        "content": row[3] if isinstance(row[3], dict) else row[3],
        "audio_url": row[4],
        "duration": row[5],
    }
