"""app/api/v1/agent.py — 交易员市场接口"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.database import get_db
from app.models.user import User
from app.models.agent import AgentTrader, UserAgent, AgentPerformance
from app.models.points import UserPoints, PointsTransaction
from app.schemas.agent import (
    AgentTraderResponse,
    AgentTraderDetail,
    AgentMarketListResponse,
    AgentPerformanceResponse,
    AgentPerformanceDetailResponse,
    HireAgentRequest,
    HireAgentResponse,
    UserAgentResponse,
    UpdateManagementModeRequest,
)
from app.api.v1.auth import get_current_user

router = APIRouter()


# ── 市场列表 ──

@router.get("/market", response_model=AgentMarketListResponse)
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取交易员市场列表"""
    q = (
        select(AgentTrader)
        .where(AgentTrader.is_active == True)
        .order_by(AgentTrader.sort_order)
    )
    rows = (await db.execute(q)).scalars().all()
    items = [AgentTraderResponse.model_validate(r) for r in rows]
    return AgentMarketListResponse(items=items, total=len(items))


# ── 交易员详情 ──

@router.get("/market/{agent_id}", response_model=AgentTraderDetail)
async def get_agent_detail(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取交易员详情（含是否已雇佣、近期表现）"""
    result = await db.execute(
        select(AgentTrader).where(AgentTrader.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="交易员不存在")

    detail = AgentTraderDetail(
        id=agent.id,
        code_name=agent.code_name,
        tag=agent.tag,
        avatar_url=agent.avatar_url,
        description=agent.description,
        strategy_detail=agent.strategy_detail,
        masters=agent.masters,
        hire_price_points=agent.hire_price_points,
        profit_share_pct=agent.profit_share_pct,
        annual_return=agent.annual_return,
        max_drawdown=agent.max_drawdown,
        sharpe_ratio=agent.sharpe_ratio,
        win_rate=agent.win_rate,
        total_trades=agent.total_trades,
        radar_scores=agent.radar_scores,
        salary_curve=agent.salary_curve,
    )

    # 检查是否已雇佣
    hire_q = select(UserAgent).where(
        and_(
            UserAgent.user_id == current_user.id,
            UserAgent.agent_id == agent_id,
            UserAgent.status == "active",
        )
    )
    hire = (await db.execute(hire_q)).scalar_one_or_none()
    if hire:
        detail.is_hired = True
        detail.management_mode = hire.management_mode
        detail.hired_at = hire.hired_at
        detail.current_pnl = float(hire.current_pnl) if hire.current_pnl else 0

    # 近期表现
    perf_q = (
        select(AgentPerformance)
        .where(AgentPerformance.agent_id == agent_id)
        .order_by(AgentPerformance.period_end.desc())
        .limit(6)
    )
    perfs = (await db.execute(perf_q)).scalars().all()
    detail.recent_performances = [
        AgentPerformanceResponse(
            period=p.period,
            period_end=p.period_end,
            return_pct=float(p.return_pct),
            benchmark_return_pct=float(p.benchmark_return_pct) if p.benchmark_return_pct else None,
            alpha=float(p.alpha) if p.alpha else None,
            max_drawdown=float(p.max_drawdown) if p.max_drawdown else None,
            sharpe_ratio=float(p.sharpe_ratio) if p.sharpe_ratio else None,
            win_rate=float(p.win_rate) if p.win_rate else None,
        )
        for p in perfs
    ]

    return detail


# ── 交易员表现详情（收益曲线+雷达图） ──

@router.get("/market/{agent_id}/performance", response_model=AgentPerformanceDetailResponse)
async def get_agent_performance(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取交易员表现详情（含收益曲线和雷达图数据）"""
    agent_result = await db.execute(
        select(AgentTrader).where(AgentTrader.id == agent_id)
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="交易员不存在")

    perf_q = (
        select(AgentPerformance)
        .where(AgentPerformance.agent_id == agent_id)
        .order_by(AgentPerformance.period_end.desc())
        .limit(12)
    )
    perfs = (await db.execute(perf_q)).scalars().all()

    salary_curve = agent.salary_curve or []
    if not salary_curve and perfs:
        salary_curve = [
            {"date": str(p.period_end), "value": float(p.return_pct)}
            for p in reversed(perfs)
        ]

    latest_perf = perfs[0] if perfs else None
    metrics = None
    if latest_perf:
        metrics = AgentPerformanceResponse(
            period=latest_perf.period,
            period_end=latest_perf.period_end,
            return_pct=float(latest_perf.return_pct),
            benchmark_return_pct=float(latest_perf.benchmark_return_pct) if latest_perf.benchmark_return_pct else None,
            alpha=float(latest_perf.alpha) if latest_perf.alpha else None,
            max_drawdown=float(latest_perf.max_drawdown) if latest_perf.max_drawdown else None,
            sharpe_ratio=float(latest_perf.sharpe_ratio) if latest_perf.sharpe_ratio else None,
            win_rate=float(latest_perf.win_rate) if latest_perf.win_rate else None,
        )

    return AgentPerformanceDetailResponse(
        agent_id=agent.id,
        performance_metrics=metrics,
        salary_curve=salary_curve,
        recent_performances=[
            AgentPerformanceResponse(
                period=p.period,
                period_end=p.period_end,
                return_pct=float(p.return_pct),
                benchmark_return_pct=float(p.benchmark_return_pct) if p.benchmark_return_pct else None,
                alpha=float(p.alpha) if p.alpha else None,
                max_drawdown=float(p.max_drawdown) if p.max_drawdown else None,
                sharpe_ratio=float(p.sharpe_ratio) if p.sharpe_ratio else None,
                win_rate=float(p.win_rate) if p.win_rate else None,
            )
            for p in perfs
        ],
    )


# ── 雇佣交易员 ──

@router.post("/market/{agent_id}/hire", response_model=HireAgentResponse)
async def hire_agent(
    agent_id: str,
    req: HireAgentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """雇佣交易员"""
    # 查交易员
    agent_result = await db.execute(
        select(AgentTrader).where(AgentTrader.id == agent_id)
    )
    agent = agent_result.scalar_one_or_none()
    if not agent or not agent.is_active:
        raise HTTPException(status_code=404, detail="交易员不存在或已下架")

    # 检查是否已雇佣
    hire_q = select(UserAgent).where(
        and_(
            UserAgent.user_id == current_user.id,
            UserAgent.agent_id == agent_id,
            UserAgent.status == "active",
        )
    )
    existing = (await db.execute(hire_q)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="已雇佣该交易员，请在我的交易员中查看")

    # 查积分
    pts_result = await db.execute(
        select(UserPoints).where(UserPoints.user_id == current_user.id)
    )
    user_pts = pts_result.scalar_one_or_none()
    if not user_pts:
        user_pts = UserPoints(user_id=current_user.id)
        db.add(user_pts)
        await db.flush()

    cost = agent.hire_price_points
    if user_pts.balance < cost:
        raise HTTPException(status_code=400, detail=f"积分不足，需要 {cost} 积分，当前余额 {user_pts.balance}")

    # 扣除积分
    user_pts.balance -= cost
    user_pts.total_spent += cost

    # 积分流水
    tx = PointsTransaction(
        user_id=current_user.id,
        amount=-cost,
        balance_after=user_pts.balance,
        tx_type="hire_agent",
        reference_id=agent.id,
        description=f"雇佣交易员「{agent.code_name}·{agent.tag}」",
    )
    db.add(tx)

    # 创建 user_agent
    from datetime import datetime, timedelta
    expires_at = datetime.now() + timedelta(days=30)

    ua = UserAgent(
        user_id=current_user.id,
        agent_id=agent.id,
        status="active",
        management_mode=req.management_mode,
        expires_at=expires_at,
    )
    db.add(ua)
    await db.flush()

    return HireAgentResponse(
        user_agent_id=ua.id,
        agent_id=agent.id,
        points_spent=cost,
        balance_after=user_pts.balance,
        management_mode=req.management_mode,
        expires_at=expires_at,
    )


# ── 我的交易员 ──

@router.get("/my-agents", response_model=list[UserAgentResponse])
async def list_my_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取我雇佣的交易员列表"""
    q = (
        select(UserAgent)
        .where(UserAgent.user_id == current_user.id)
        .order_by(UserAgent.hired_at.desc())
    )
    rows = (await db.execute(q)).scalars().all()

    items = []
    for ua in rows:
        agent_result = await db.execute(
            select(AgentTrader).where(AgentTrader.id == ua.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        items.append(UserAgentResponse(
            id=ua.id,
            agent_id=ua.agent_id,
            agent=AgentTraderResponse.model_validate(agent) if agent else None,
            status=ua.status,
            management_mode=ua.management_mode,
            allocated_capital=float(ua.allocated_capital) if ua.allocated_capital else None,
            current_pnl=float(ua.current_pnl) if ua.current_pnl else None,
            hired_at=ua.hired_at,
            expires_at=ua.expires_at,
        ))
    return items


# ── 切换管理模式 ──

@router.patch("/my-agents/{user_agent_id}/mode")
async def update_management_mode(
    user_agent_id: int,
    req: UpdateManagementModeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """切换管理模式"""
    result = await db.execute(
        select(UserAgent).where(
            and_(UserAgent.id == user_agent_id, UserAgent.user_id == current_user.id)
        )
    )
    ua = result.scalar_one_or_none()
    if not ua:
        raise HTTPException(status_code=404, detail="交易员不存在")

    ua.management_mode = req.management_mode
    mode_label = "完全托管" if req.management_mode == "full_managed" else "建议模式"
    return {"success": True, "user_agent_id": ua.id, "management_mode": req.management_mode, "message": f"已切换为{mode_label}"}


# ── 解雇（停用）交易员 ──

@router.delete("/my-agents/{user_agent_id}")
async def dismiss_agent(
    user_agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """解雇（停用）交易员"""
    result = await db.execute(
        select(UserAgent).where(
            and_(UserAgent.id == user_agent_id, UserAgent.user_id == current_user.id)
        )
    )
    ua = result.scalar_one_or_none()
    if not ua:
        raise HTTPException(status_code=404, detail="交易员不存在")

    ua.status = "expired"
    return {"success": True, "message": "已解雇该交易员"}
