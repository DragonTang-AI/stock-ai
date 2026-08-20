"""
app/api/v1/admin/watchlists.py — 自选股管理

能力：
  GET  /list        自选列表（用户名/股票代码模糊搜索 + 分页）
  DELETE /{id}      删除单条自选

数据源：watchlists / users
"""
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin, require_permission
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.operation_log import OperationLog
from app.models.stock import Watchlist
from app.models.user import User

router = APIRouter()

PERM_VIEW = "watchlists:view"
PERM_MANAGE = "watchlists:manage"


def _f(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return v


async def _log(db: AsyncSession, admin: AdminUser, action: str, detail: str = "") -> None:
    db.add(
        OperationLog(
            user_id=admin.id,
            username=admin.username,
            module="watchlists",
            action=action,
            detail=detail[:500],
            ip="",
        )
    )


@router.get("/list")
async def watchlist_list(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM_VIEW)),
    keyword: str = Query("", description="用户名/股票代码模糊搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """自选列表（用户名/代码筛选 + 分页）"""
    conds = []
    if keyword:
        like = f"%{keyword}%"
        conds.append(User.username.ilike(like) | Watchlist.symbol.ilike(like))

    base = (
        select(
            Watchlist.id,
            Watchlist.symbol,
            Watchlist.note,
            Watchlist.sort_order,
            Watchlist.created_at,
            User.id.label("user_id"),
            User.username,
        )
        .join(User, User.id == Watchlist.user_id)
        .where(*conds)
    )
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    rows = (
        await db.execute(
            base.order_by(desc(Watchlist.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    items = [
        {
            "id": r.id,
            "user_id": r.user_id,
            "username": r.username,
            "symbol": r.symbol,
            "note": r.note,
            "sort_order": r.sort_order,
            "created_at": _f(r.created_at),
        }
        for r in rows
    ]
    return {"code": 0, "data": {"items": items, "total": total}, "message": "ok"}


@router.delete("/{item_id}")
async def delete_watchlist(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(PERM_MANAGE)),
):
    """删除单条自选记录"""
    item = await db.get(Watchlist, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="自选记录不存在")
    user = await db.get(User, item.user_id)
    uname = user.username if user else str(item.user_id)
    await db.delete(item)
    await _log(
        db,
        admin,
        "delete",
        f"删除用户 {uname}({item.user_id}) 的自选 {item.symbol}",
    )
    await db.commit()
    return {"code": 0, "data": {"id": item_id}, "message": "ok"}
