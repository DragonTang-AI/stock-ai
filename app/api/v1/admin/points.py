"""
app/api/v1/admin/points.py — 积分管理

能力：
  GET  /list                    积分列表（用户名关键词/分页）
  GET  /{user_id}/transactions  积分流水（分页）
  POST /{user_id}/adjust        调整积分（可正可负，写流水 + 操作日志）

数据源：users / user_points / agent.points_transactions
"""
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin, require_permission
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.models.operation_log import OperationLog
from app.models.points import PointsTransaction, UserPoints
from app.models.user import User

router = APIRouter()

PERM_VIEW = "points:view"
PERM_MANAGE = "points:manage"


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
            module="points",
            action=action,
            detail=detail[:500],
            ip="",
        )
    )


@router.get("/list")
async def points_list(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM_VIEW)),
    keyword: str = Query("", description="用户名模糊搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """积分列表（含用户名关键词筛选 + 最近流水时间）"""
    conds = []
    if keyword:
        conds.append(User.username.ilike(f"%{keyword}%"))

    base = (
        select(
            User.id,
            User.username,
            User.email,
            User.is_active,
            User.created_at,
            UserPoints.balance,
            UserPoints.total_earned,
            UserPoints.total_spent,
            UserPoints.updated_at,
        )
        .outerjoin(UserPoints, UserPoints.user_id == User.id)
        .where(*conds)
    )
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    rows = (
        await db.execute(
            base.order_by(desc(func.coalesce(UserPoints.updated_at, User.created_at)))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    user_ids = [r.id for r in rows]
    last_tx = {}
    if user_ids:
        txs = (
            await db.execute(
                select(
                    PointsTransaction.user_id,
                    func.max(PointsTransaction.created_at).label("last"),
                )
                .where(PointsTransaction.user_id.in_(user_ids))
                .group_by(PointsTransaction.user_id)
            )
        ).all()
        last_tx = {t.user_id: _f(t.last) for t in txs}

    items = [
        {
            "user_id": r.id,
            "username": r.username,
            "email": r.email,
            "is_active": r.is_active,
            "balance": r.balance if r.balance is not None else 0,
            "total_earned": r.total_earned if r.total_earned is not None else 0,
            "total_spent": r.total_spent if r.total_spent is not None else 0,
            "updated_at": _f(r.updated_at),
            "last_tx_at": last_tx.get(r.id),
        }
        for r in rows
    ]
    return {
        "code": 0,
        "data": {"items": items, "total": total, "page": page, "page_size": page_size},
        "message": "ok",
    }


@router.get("/{user_id}/transactions")
async def points_transactions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(require_permission(PERM_VIEW)),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """指定用户的积分流水"""
    base = select(PointsTransaction).where(PointsTransaction.user_id == user_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    rows = (
        await db.execute(
            base.order_by(desc(PointsTransaction.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    items = [
        {
            "id": t.id,
            "user_id": t.user_id,
            "amount": t.amount,
            "balance_after": t.balance_after,
            "tx_type": t.tx_type,
            "reference_id": t.reference_id,
            "description": t.description,
            "created_at": _f(t.created_at),
        }
        for t in rows
    ]
    return {"code": 0, "data": {"items": items, "total": total}, "message": "ok"}


class AdjustBody(BaseModel):
    delta: int = Field(..., description="积分变动值，正数增加负数扣减，不可为0")
    reason: str = Field("", max_length=200, description="调整原因")


@router.post("/{user_id}/adjust")
async def adjust_points(
    user_id: int,
    body: AdjustBody,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission(PERM_MANAGE)),
):
    """调整积分：正数增加、负数扣减，写入流水与操作日志"""
    if body.delta == 0:
        raise HTTPException(status_code=400, detail="积分变动值不能为0")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    up = await db.get(UserPoints, user_id)
    if up is None:
        up = UserPoints(user_id=user_id, balance=100, total_earned=100, total_spent=0)
        db.add(up)
        await db.flush()

    new_balance = up.balance + body.delta
    if new_balance < 0:
        raise HTTPException(
            status_code=400,
            detail=f"积分不足：当前 {up.balance}，无法扣减 {abs(body.delta)}",
        )

    old_balance = up.balance
    up.balance = new_balance
    if body.delta > 0:
        up.total_earned += body.delta
    else:
        up.total_spent += abs(body.delta)

    db.add(
        PointsTransaction(
            user_id=user_id,
            amount=body.delta,
            balance_after=new_balance,
            tx_type="admin_adjust",
            reference_id=f"admin:{admin.id}",
            description=body.reason or "管理员调整",
        )
    )
    await _log(
        db,
        admin,
        "adjust",
        f"调整用户 {user.username}({user_id}) 积分 {body.delta:+,} → {new_balance}，原因：{body.reason or '无'}",
    )
    await db.commit()
    return {
        "code": 0,
        "data": {
            "user_id": user_id,
            "username": user.username,
            "old_balance": old_balance,
            "delta": body.delta,
            "balance": new_balance,
        },
        "message": "ok",
    }
