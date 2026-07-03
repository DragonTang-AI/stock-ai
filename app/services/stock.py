"""
app.services.stock — 自选股/关注列表服务

功能：
- 添加/删除/查询自选股
- 批量添加
- 查询时自动补充实时行情（价格、涨跌幅）
"""
import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Watchlist
from app.schemas.stock import WatchlistItem, WatchlistCreate, WatchlistUpdate
from app.services.market import fetch_realtime_quotes

logger = logging.getLogger(__name__)


async def list_watchlist(
    db: AsyncSession, user_id: int
) -> List[WatchlistItem]:
    """
    查询用户的全部自选股，按 sort_order 升序、created_at 降序排列。
    自动拉取实时行情补充价格和涨跌幅。
    """
    stmt = (
        select(Watchlist)
        .where(Watchlist.user_id == user_id)
        .order_by(Watchlist.sort_order.asc(), Watchlist.created_at.desc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    if not records:
        return []

    # 收集代码列表
    symbols = [r.symbol for r in records]

    # 批量拉取实时行情（失败不影响返回）
    quotes_map = {}
    try:
        quotes = await fetch_realtime_quotes(symbols)
        for q in quotes:
            quotes_map[q.symbol] = q
    except Exception as e:
        logger.warning(f"自选股补充行情失败: {e}")

    items = []
    for r in records:
        q = quotes_map.get(r.symbol)
        items.append(WatchlistItem(
            id=r.id,
            symbol=r.symbol,
            name=q.name if q else r.symbol,
            price=q.price if q else None,
            change_pct=q.change_pct if q else None,
            note=r.note,
            sort_order=r.sort_order,
            created_at=r.created_at,
        ))

    return items


async def add_watchlist(
    db: AsyncSession, user_id: int, create: WatchlistCreate
) -> Optional[WatchlistItem]:
    """
    添加自选股。如已存在则跳过（幂等）。
    """
    # 检查是否已存在
    stmt = select(Watchlist).where(
        Watchlist.user_id == user_id,
        Watchlist.symbol == create.symbol,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # 已存在，返回现有记录
        q = None
        try:
            quotes = await fetch_realtime_quotes([existing.symbol])
            if quotes:
                q = quotes[0]
        except Exception:
            pass
        return WatchlistItem(
            id=existing.id,
            symbol=existing.symbol,
            name=q.name if q else existing.symbol,
            price=q.price if q else None,
            change_pct=q.change_pct if q else None,
            note=existing.note,
            sort_order=existing.sort_order,
            created_at=existing.created_at,
        )

    # 获取下一个 sort_order（追加到最后）
    max_order = await db.execute(
        select(func.coalesce(func.max(Watchlist.sort_order), -1))
        .where(Watchlist.user_id == user_id)
    )
    next_order = max_order.scalar() + 1

    record = Watchlist(
        user_id=user_id,
        symbol=create.symbol,
        note=create.note,
        sort_order=next_order,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # 补充行情
    q = None
    try:
        quotes = await fetch_realtime_quotes([record.symbol])
        if quotes:
            q = quotes[0]
    except Exception:
        pass

    return WatchlistItem(
        id=record.id,
        symbol=record.symbol,
        name=q.name if q else record.symbol,
        price=q.price if q else None,
        change_pct=q.change_pct if q else None,
        note=record.note,
        sort_order=record.sort_order,
        created_at=record.created_at,
    )


async def remove_watchlist(
    db: AsyncSession, user_id: int, symbol: str
) -> bool:
    """删除自选股。未找到时返回 False。"""
    stmt = select(Watchlist).where(
        Watchlist.user_id == user_id,
        Watchlist.symbol == symbol,
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        return False

    await db.delete(record)
    await db.commit()
    return True


async def update_watchlist(
    db: AsyncSession, user_id: int, symbol: str, update: WatchlistUpdate
) -> Optional[WatchlistItem]:
    """更新自选股（备注/排序）"""
    stmt = select(Watchlist).where(
        Watchlist.user_id == user_id,
        Watchlist.symbol == symbol,
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        return None

    if update.note is not None:
        record.note = update.note
    if update.sort_order is not None:
        record.sort_order = update.sort_order

    await db.commit()
    await db.refresh(record)

    # 补充行情
    q = None
    try:
        quotes = await fetch_realtime_quotes([record.symbol])
        if quotes:
            q = quotes[0]
    except Exception:
        pass

    return WatchlistItem(
        id=record.id,
        symbol=record.symbol,
        name=q.name if q else record.symbol,
        price=q.price if q else None,
        change_pct=q.change_pct if q else None,
        note=record.note,
        sort_order=record.sort_order,
        created_at=record.created_at,
    )


async def check_watchlist(
    db: AsyncSession, user_id: int, symbol: str
) -> bool:
    """检查某只股票是否已在自选"""
    stmt = select(Watchlist).where(
        Watchlist.user_id == user_id,
        Watchlist.symbol == symbol,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def batch_add_watchlist(
    db: AsyncSession, user_id: int, symbols: List[str]
) -> List[WatchlistItem]:
    """批量添加自选股（跳过已存在）"""
    items = []
    for sym in symbols:
        item = await add_watchlist(db, user_id, WatchlistCreate(symbol=sym))
        if item:
            items.append(item)
    return items
