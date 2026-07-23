"""
app/api/v1/agent_console.py — 交易员控制台接口
"""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case, desc
from app.core.database import get_db
from app.models.user import User
from app.models.agent import AgentTrader, UserAgent, AgentSignal, AgentPortfolio
from app.schemas.agent import (
    ConsoleOverviewResponse,
    ConsoleSignalResponse,
    ConsolePortfolioResponse,
    ConsoleTradeResponse,
    EquityCurvePoint,
    SignalConfirmRequest,
)
from app.api.v1.auth import get_current_user

router = APIRouter()

# ── 热门 A 股股票池 ──

HOT_STOCKS = [
    {"symbol": "600519", "name": "贵州茅台"},
    {"symbol": "300750", "name": "宁德时代"},
    {"symbol": "002594", "name": "比亚迪"},
    {"symbol": "000858", "name": "五粮液"},
    {"symbol": "601318", "name": "中国平安"},
    {"symbol": "000333", "name": "美的集团"},
    {"symbol": "600036", "name": "招商银行"},
    {"symbol": "002475", "name": "立讯精密"},
    {"symbol": "300059", "name": "东方财富"},
    {"symbol": "601012", "name": "隆基绿能"},
    {"symbol": "600276", "name": "恒瑞医药"},
    {"symbol": "002415", "name": "海康威视"},
    {"symbol": "300124", "name": "汇川技术"},
    {"symbol": "600900", "name": "长江电力"},
    {"symbol": "002371", "name": "北方华创"},
    {"symbol": "300274", "name": "阳光电源"},
    {"symbol": "601899", "name": "紫金矿业"},
    {"symbol": "600809", "name": "山西汾酒"},
    {"symbol": "300760", "name": "迈瑞医疗"},
    {"symbol": "002142", "name": "宁波银行"},
]

# ── 辅助函数 ──

async def _get_hire_or_404(db: AsyncSession, hire_id: int, user_id: int) -> UserAgent:
    result = await db.execute(
        select(UserAgent).where(
            and_(UserAgent.id == hire_id, UserAgent.user_id == user_id)
        )
    )
    hire = result.scalar_one_or_none()
    if not hire:
        raise HTTPException(status_code=404, detail="雇佣关系不存在")
    return hire


# ── 控制台概览 ──

@router.get("/{hire_id}/overview", response_model=ConsoleOverviewResponse)
async def get_console_overview(
    hire_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hire = await _get_hire_or_404(db, hire_id, current_user.id)

    # 交易员信息
    agent_result = await db.execute(
        select(AgentTrader).where(AgentTrader.id == hire.agent_id)
    )
    trader = agent_result.scalar_one_or_none()

    # 总资产 & 浮动盈亏（从持仓汇总）
    pf_result = await db.execute(
        select(
            func.coalesce(func.sum(AgentPortfolio.market_value), 0).label("total_value"),
            func.coalesce(func.sum(AgentPortfolio.unrealized_pnl), 0).label("total_pnl"),
            func.coalesce(func.count(), 0).label("position_count"),
        ).where(AgentPortfolio.hire_id == hire_id)
    )
    pf_row = pf_result.one()
    total_assets = float(pf_row.total_value)
    total_pnl = float(pf_row.total_pnl)
    position_count = pf_row.position_count

    # 今日信号数
    today = date.today()
    sig_result = await db.execute(
        select(func.count()).where(
            and_(
                AgentSignal.hire_id == hire_id,
                func.date(AgentSignal.created_at) == today,
            )
        )
    )
    today_signals = sig_result.scalar() or 0

    # 待处理信号数
    pending_result = await db.execute(
        select(func.count()).where(
            and_(
                AgentSignal.hire_id == hire_id,
                AgentSignal.exec_status == "pending",
            )
        )
    )
    pending_signals = pending_result.scalar() or 0

    return ConsoleOverviewResponse(
        hire_id=hire_id,
        trader_name=trader.code_name if trader else "--",
        trader_tag=trader.tag if trader else "",
        management_mode=hire.management_mode,
        status=hire.status,
        total_assets=total_assets,
        unrealized_pnl=total_pnl,
        today_signals=today_signals,
        pending_signals=pending_signals,
        position_count=position_count,
    )


# ── 信号列表 ──

@router.get("/{hire_id}/signals", response_model=list[ConsoleSignalResponse])
async def list_signals(
    hire_id: int,
    status: str | None = Query(default=None, description="筛选状态: pending/confirmed/ignored/auto_executed"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_hire_or_404(db, hire_id, current_user.id)

    conditions = [AgentSignal.hire_id == hire_id]
    if status:
        conditions.append(AgentSignal.exec_status == status)

    q = (
        select(AgentSignal)
        .where(and_(*conditions))
        .order_by(desc(AgentSignal.created_at))
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(q)).scalars().all()

    return [
        ConsoleSignalResponse(
            id=row.id,
            hire_id=row.hire_id,
            trader_id=row.trader_id,
            symbol=row.symbol,
            symbol_name=row.symbol_name,
            action=row.action,
            price=float(row.price),
            quantity=row.quantity,
            confidence=row.confidence,
            reasoning=row.reasoning,
            exec_status=row.exec_status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


# ── 确认信号 ──

@router.post("/signals/{signal_id}/confirm")
async def confirm_signal(
    signal_id: int,
    req: SignalConfirmRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentSignal).where(
            and_(AgentSignal.id == signal_id, AgentSignal.user_id == current_user.id)
        )
    )
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=404, detail="信号不存在")
    if signal.exec_status != "pending":
        raise HTTPException(status_code=400, detail=f"信号状态为 {signal.exec_status}，无法确认")

    # 更新数量（如果提供）
    if req and req.quantity:
        signal.quantity = req.quantity

    signal.exec_status = "confirmed"
    signal.updated_at = datetime.now()
    await db.flush()

    # 同步到持仓
    pf_result = await db.execute(
        select(AgentPortfolio).where(
            and_(
                AgentPortfolio.hire_id == signal.hire_id,
                AgentPortfolio.symbol == signal.symbol,
            )
        )
    )
    portfolio = pf_result.scalar_one_or_none()

    if signal.action == "buy":
        if portfolio:
            # 加仓：重新计算平均成本
            total_cost = float(portfolio.avg_cost) * portfolio.quantity + float(signal.price) * signal.quantity
            portfolio.quantity += signal.quantity
            portfolio.avg_cost = total_cost / portfolio.quantity
        else:
            portfolio = AgentPortfolio(
                hire_id=signal.hire_id,
                trader_id=signal.trader_id,
                user_id=signal.user_id,
                symbol=signal.symbol,
                symbol_name=signal.symbol_name,
                quantity=signal.quantity,
                avg_cost=signal.price,
                current_price=signal.price,
                market_value=float(signal.price) * signal.quantity,
                unrealized_pnl=0,
            )
            db.add(portfolio)
    elif signal.action == "sell" and portfolio:
        if portfolio.quantity >= signal.quantity:
            portfolio.quantity -= signal.quantity
            if portfolio.quantity == 0:
                await db.delete(portfolio)
            else:
                portfolio.market_value = float(portfolio.current_price or signal.price) * portfolio.quantity
                portfolio.unrealized_pnl = portfolio.market_value - float(portfolio.avg_cost) * portfolio.quantity

    return {"success": True, "signal_id": signal_id, "message": "信号已确认执行"}


# ── 忽略信号 ──

@router.post("/signals/{signal_id}/ignore")
async def ignore_signal(
    signal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentSignal).where(
            and_(AgentSignal.id == signal_id, AgentSignal.user_id == current_user.id)
        )
    )
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=404, detail="信号不存在")
    if signal.exec_status != "pending":
        raise HTTPException(status_code=400, detail=f"信号状态为 {signal.exec_status}，无法忽略")

    signal.exec_status = "ignored"
    signal.updated_at = datetime.now()

    return {"success": True, "signal_id": signal_id, "message": "信号已忽略"}


# ── 当前持仓 ──

@router.get("/{hire_id}/portfolio", response_model=list[ConsolePortfolioResponse])
async def get_agent_portfolio(
    hire_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_hire_or_404(db, hire_id, current_user.id)

    q = select(AgentPortfolio).where(
        and_(AgentPortfolio.hire_id == hire_id, AgentPortfolio.quantity > 0)
    ).order_by(desc(AgentPortfolio.market_value))

    rows = (await db.execute(q)).scalars().all()

    return [
        ConsolePortfolioResponse(
            id=row.id,
            hire_id=row.hire_id,
            symbol=row.symbol,
            symbol_name=row.symbol_name,
            quantity=row.quantity,
            avg_cost=float(row.avg_cost),
            current_price=float(row.current_price) if row.current_price else None,
            market_value=float(row.market_value) if row.market_value else None,
            unrealized_pnl=float(row.unrealized_pnl) if row.unrealized_pnl else None,
        )
        for row in rows
    ]


# ── 交易日志 ──

@router.get("/{hire_id}/trades", response_model=list[ConsoleTradeResponse])
async def get_agent_trades(
    hire_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_hire_or_404(db, hire_id, current_user.id)

    q = (
        select(AgentSignal)
        .where(
            and_(
                AgentSignal.hire_id == hire_id,
                AgentSignal.exec_status.in_(["confirmed", "auto_executed"]),
            )
        )
        .order_by(desc(AgentSignal.updated_at))
        .limit(limit)
    )
    rows = (await db.execute(q)).scalars().all()

    return [
        ConsoleTradeResponse(
            id=row.id,
            symbol=row.symbol,
            symbol_name=row.symbol_name,
            action=row.action,
            price=float(row.price),
            quantity=row.quantity,
            confidence=row.confidence,
            reasoning=row.reasoning,
            exec_status=row.exec_status,
            executed_at=row.updated_at,
        )
        for row in rows
    ]


# ── 权益曲线 ──

@router.get("/{hire_id}/equity-curve", response_model=list[EquityCurvePoint])
async def get_equity_curve(
    hire_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按日汇总的权益曲线数据"""
    await _get_hire_or_404(db, hire_id, current_user.id)

    # 获取所有已执行信号，按日汇总模拟权益变化
    q = (
        select(
            func.date(AgentSignal.updated_at).label("trade_date"),
            func.sum(
                case(
                    (AgentSignal.action == "buy", -func.coalesce(AgentSignal.price, 0) * AgentSignal.quantity),
                    (AgentSignal.action == "sell", func.coalesce(AgentSignal.price, 0) * AgentSignal.quantity),
                    else_=0,
                )
            ).label("daily_pnl"),
        )
        .where(
            and_(
                AgentSignal.hire_id == hire_id,
                AgentSignal.exec_status.in_(["confirmed", "auto_executed"]),
            )
        )
        .group_by(func.date(AgentSignal.updated_at))
        .order_by(func.date(AgentSignal.updated_at))
    )
    rows = (await db.execute(q)).all()

    equity = 0.0
    points = []
    for row in rows:
        equity += float(row.daily_pnl)
        points.append(EquityCurvePoint(
            date=str(row.trade_date),
            equity=round(equity, 2),
            daily_pnl=round(float(row.daily_pnl), 2),
        ))

    # 如果数据为空，补充一些模拟起点数据
    if not points:
        base = 100000
        for i in range(7):
            d = date.today()
            from datetime import timedelta
            d = d - timedelta(days=6 - i)
            equity = base + i * 500
            points.append(EquityCurvePoint(
                date=str(d),
                equity=equity,
                daily_pnl=500 if i > 0 else 0,
            ))

    return points


# ── 手动生成模拟信号 ──

@router.post("/{hire_id}/generate-signals", response_model=list[ConsoleSignalResponse])
async def generate_signals(
    hire_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动触发生成 1-3 条模拟交易信号"""
    import random

    hire = await _get_hire_or_404(db, hire_id, current_user.id)

    count = random.randint(1, 3)
    selected = random.sample(HOT_STOCKS, min(count, len(HOT_STOCKS)))

    signals = []
    for stock in selected:
        action = random.choice(["buy", "sell"])
        base_price = random.uniform(10, 500)
        price = round(base_price, 2)
        quantity = random.choice([100, 200, 300, 500])
        confidence = random.randint(40, 95)

        if action == "buy":
            reasons = [
                f"技术面突破关键阻力位，MACD金叉信号出现，成交量放大",
                f"基本面估值偏低，PEG<1，行业景气度回升",
                f"北向资金持续流入，机构持仓比例提升",
                f"季报超预期，营收同比增长20%+，毛利率改善",
            ]
        else:
            reasons = [
                f"估值已处于历史高位区间，止盈建议",
                f"技术面量价背离，短期回调压力增大",
                f"行业政策风险升温，建议降低仓位",
                f"达到目标价位，建议分批止盈",
            ]

        signal = AgentSignal(
            hire_id=hire_id,
            trader_id=hire.agent_id,
            user_id=current_user.id,
            symbol=stock["symbol"],
            symbol_name=stock["name"],
            action=action,
            price=price,
            quantity=quantity,
            confidence=confidence,
            reasoning=random.choice(reasons),
            exec_status="auto_executed" if hire.management_mode == "full_managed" else "pending",
        )
        db.add(signal)
        await db.flush()

        signals.append(ConsoleSignalResponse(
            id=signal.id,
            hire_id=signal.hire_id,
            trader_id=signal.trader_id,
            symbol=signal.symbol,
            symbol_name=signal.symbol_name,
            action=signal.action,
            price=float(signal.price),
            quantity=signal.quantity,
            confidence=signal.confidence,
            reasoning=signal.reasoning,
            exec_status=signal.exec_status,
            created_at=signal.created_at,
            updated_at=signal.updated_at,
        ))

    return signals
