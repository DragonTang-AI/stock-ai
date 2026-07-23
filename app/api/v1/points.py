"""app/api/v1/points.py — 积分系统接口"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.user import User
from app.models.points import UserPoints, PointsTransaction
from app.schemas.points import (
    PointsBalanceResponse,
    PointsHistoryResponse,
    PointsTransactionResponse,
    DailyCheckinResponse,
)
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.get("/balance", response_model=PointsBalanceResponse)
async def get_points_balance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户积分余额"""
    result = await db.execute(
        select(UserPoints).where(UserPoints.user_id == current_user.id)
    )
    points = result.scalar_one_or_none()
    if not points:
        points = UserPoints(user_id=current_user.id)
        db.add(points)
        await db.flush()
    return PointsBalanceResponse(
        balance=points.balance,
        total_earned=points.total_earned,
        total_spent=points.total_spent,
        updated_at=points.updated_at,
    )


@router.get("/history", response_model=PointsHistoryResponse)
async def get_points_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取积分流水"""
    count_q = select(func.count()).select_from(PointsTransaction).where(
        PointsTransaction.user_id == current_user.id
    )
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(PointsTransaction)
        .where(PointsTransaction.user_id == current_user.id)
        .order_by(PointsTransaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(q)).scalars().all()

    items = [PointsTransactionResponse.model_validate(r) for r in rows]
    return PointsHistoryResponse(items=items, total=total)


@router.post("/daily-checkin", response_model=DailyCheckinResponse)
async def daily_checkin(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """每日签到"""
    from datetime import datetime, date, timedelta

    today = date.today()

    # 查询用户积分
    result = await db.execute(
        select(UserPoints).where(UserPoints.user_id == current_user.id)
    )
    points = result.scalar_one_or_none()
    if not points:
        points = UserPoints(user_id=current_user.id)
        db.add(points)
        await db.flush()

    # 检查今天是否已签到
    check_q = (
        select(PointsTransaction)
        .where(
            PointsTransaction.user_id == current_user.id,
            PointsTransaction.tx_type == "daily_checkin",
        )
        .order_by(PointsTransaction.created_at.desc())
        .limit(1)
    )
    last_checkin = (await db.execute(check_q)).scalar_one_or_none()

    if last_checkin and last_checkin.created_at.date() == today:
        return DailyCheckinResponse(
            success=False,
            points_earned=0,
            balance=points.balance,
            consecutive_days=0,
        )

    # 计算连续签到天数
    consecutive = 0
    if last_checkin:
        diff = (today - last_checkin.created_at.date()).days
        if diff == 1:
            # 需要查前 N 条
            history_q = (
                select(PointsTransaction)
                .where(
                    PointsTransaction.user_id == current_user.id,
                    PointsTransaction.tx_type == "daily_checkin",
                )
                .order_by(PointsTransaction.created_at.desc())
                .limit(30)
            )
            history = (await db.execute(history_q)).scalars().all()
            consecutive = 1
            for i in range(1, len(history)):
                if (history[i-1].created_at.date() - history[i].created_at.date()).days == 1:
                    consecutive += 1
                else:
                    break

    consecutive += 1
    earn = 5 + min(consecutive - 1, 7) * 2  # 第1天5分, 之后每天+2, 最多19分

    # 更新积分
    points.balance += earn
    points.total_earned += earn

    tx = PointsTransaction(
        user_id=current_user.id,
        amount=earn,
        balance_after=points.balance,
        tx_type="daily_checkin",
        description=f"连续签到第{consecutive}天",
    )
    db.add(tx)

    return DailyCheckinResponse(
        success=True,
        points_earned=earn,
        balance=points.balance,
        consecutive_days=consecutive,
    )
