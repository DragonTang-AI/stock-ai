"""
app/api/v1/watchlist.py — 自选股/关注列表路由

端点：
- GET    /watchlist          — 查询自选股列表
- POST   /watchlist          — 添加自选股
- PATCH  /watchlist/{symbol} — 更新自选股（备注/排序）
- DELETE /watchlist/{symbol} — 删除自选股
- GET    /watchlist/check    — 检查某只股票是否在自选
- POST   /watchlist/batch    — 批量添加

所有端点需登录（JWT）。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.models.user import User
from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.schemas.stock import (
    WatchlistResponse,
    WatchlistCreate,
    WatchlistUpdate,
    WatchlistAddResponse,
    WatchlistRemoveResponse,
    WatchlistCheckResponse,
    WatchlistBatchRequest,
    WatchlistItem,
)
from app.services.stock import (
    list_watchlist,
    add_watchlist,
    remove_watchlist,
    update_watchlist,
    check_watchlist,
    batch_add_watchlist,
)

router = APIRouter(tags=["自选股"])


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询我的自选股列表（含实时行情）"""
    items = await list_watchlist(db, current_user.id)
    return WatchlistResponse(success=True, data=items, total=len(items))


@router.post("", response_model=WatchlistAddResponse, status_code=201)
async def add_to_watchlist(
    create: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加一只股票到自选（幂等，已存在返回现有记录）"""
    item = await add_watchlist(db, current_user.id, create)
    if not item:
        raise HTTPException(status_code=500, detail="添加自选失败")
    return WatchlistAddResponse(success=True, data=item, message="添加成功")


@router.patch("/{symbol}", response_model=WatchlistAddResponse)
async def update_watchlist_item(
    symbol: str,
    update: WatchlistUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新自选股（备注/排序）"""
    item = await update_watchlist(db, current_user.id, symbol.upper(), update)
    if not item:
        raise HTTPException(status_code=404, detail="未找到该自选股")
    return WatchlistAddResponse(success=True, data=item, message="更新成功")


@router.delete("/{symbol}", response_model=WatchlistRemoveResponse)
async def remove_from_watchlist(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除自选股"""
    ok = await remove_watchlist(db, current_user.id, symbol.upper())
    if not ok:
        raise HTTPException(status_code=404, detail="未找到该自选股")
    return WatchlistRemoveResponse(success=True, message="删除成功")


@router.get("/check", response_model=WatchlistCheckResponse)
async def check_watchlist_status(
    symbol: str = Query(..., min_length=5, max_length=20,
                        description="股票代码，如 600519.SH"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """检查某只股票是否在自选列表中"""
    is_watching = await check_watchlist(db, current_user.id, symbol.upper())
    return WatchlistCheckResponse(success=True, is_watching=is_watching)


@router.post("/batch", response_model=WatchlistResponse, status_code=201)
async def batch_add_watchlist_endpoint(
    batch: WatchlistBatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量添加自选股（跳过已存在）"""
    items = await batch_add_watchlist(db, current_user.id, batch.symbols)
    return WatchlistResponse(success=True, data=items, total=len(items))
