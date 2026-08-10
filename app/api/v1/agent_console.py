import logging
"""
app/api/v1/agent_console.py — 交易员控制台接口
"""
from datetime import date, datetime, timezone
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
from app.schemas.trading import OrderRequest
from app.services import trading as trading_service
from app.core.exceptions import AppException
from app.engine.market_hours import is_market_hours, is_hk_market_hours, is_any_market_hours

router = APIRouter()
logger = logging.getLogger(__name__)

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

def _normalize_to_trading_symbol(raw_symbol: str) -> str:
    s = raw_symbol.strip()
    if '.' in s:
        return s.upper()
    if s.startswith('6'):
        return f'{s}.SH'
    elif s.startswith(('0', '3')):
        return f'{s}.SZ'
    elif s.startswith(('4', '8')):
        return f'{s}.BJ'
    # 港股裸代码（5位数字，以0开头）→ .HK
    if s.isdigit() and len(s) == 5 and s.startswith('0'):
        return f'{s}.HK'
    return s.upper()


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
        logger.warning(f"确认信号失败: 信号不存在 user_id={current_user.id} signal_id={signal_id}")
        raise HTTPException(status_code=404, detail="信号不存在")
    if signal.exec_status != "pending":
        logger.warning(f"确认信号失败: 状态为{signal.exec_status} user_id={current_user.id} signal_id={signal_id}")
        raise HTTPException(status_code=400, detail=f"信号状态为 {signal.exec_status}，无法确认")

    # 非交易时段不允许确认（按信号市场区分）
    is_hk = signal.symbol.upper().endswith(".HK") or (signal.symbol.isdigit() and len(signal.symbol) == 5 and signal.symbol.startswith("0"))
    market_in_hours = is_hk_market_hours() if is_hk else is_market_hours()
    if not market_in_hours:
        market_name = "港股" if is_hk else "A股"
        logger.warning(f"确认信号失败: 非交易时段 user_id={current_user.id} signal_id={signal_id} market={market_name}")
        raise HTTPException(status_code=400, detail=f"当前非{market_name}交易时段，无法确认信号")

    if req and req.quantity:
        signal.quantity = req.quantity

    trading_symbol = _normalize_to_trading_symbol(signal.symbol)
    # 交易单位取整
    raw_qty = int(signal.quantity)
    if is_hk:
        try:
            from app.services.hk_lot_size import get_lot_size
            code = signal.symbol.replace(".HK", "").replace(".hk", "")
            lot = get_lot_size(code) or 100
        except Exception:
            lot = 100
        if signal.action == "sell":
            lot_qty = max(lot, (raw_qty // lot) * lot)
        else:
            lot_qty = max(lot, ((raw_qty + lot - 1) // lot) * lot)
    else:
        if signal.action == "sell":
            lot_qty = max(100, (raw_qty // 100) * 100)
        else:
            lot_qty = max(100, ((raw_qty + 99) // 100) * 100)
    order_result = None
    trading_error = None

    try:
        order_req = OrderRequest(
            symbol=trading_symbol,
            side=signal.action,
            quantity=lot_qty,
            price=float(signal.price),
            order_type="market",
        )
        sig_id = f"sig_{current_user.id}_{signal.symbol}_{int(datetime.now(timezone.utc).timestamp())}"
        order_result = await trading_service.place_order(
            db=db,
            user=current_user,
            req=order_req,
            fallback_price=float(signal.price),
            signal_id=sig_id,
        )
    except AppException as e:
        trading_error = {"code": e.code, "message": e.message}
    except HTTPException:
        raise
    except Exception as e:
        trading_error = {"code": "TRADING_FAILED", "message": str(e)}

    if trading_error:
        signal.exec_status = "failed"
        signal.updated_at = datetime.now(timezone.utc)
        await db.flush()
        logger.warning(f"确认信号失败 user_id={current_user.id} signal_id={signal_id} symbol={signal.symbol} action={signal.action} error={trading_error}")
        await _update_trader_stats(db, signal.trader_id)
        return {"success": False, "signal_id": signal_id, "message": "下单失败，信号已标记为失败", "error": trading_error}

    signal.exec_status = "confirmed"
    signal.updated_at = datetime.now(timezone.utc)
    await db.flush()
    logger.info(f"确认信号成功 user_id={current_user.id} signal_id={signal_id} symbol={signal.symbol} action={signal.action} qty={lot_qty} order_ok={order_result is not None}")

    if order_result is not None:
        actual_price = order_result.filled_price
        actual_qty = order_result.filled_quantity
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
                total_cost = float(portfolio.avg_cost) * portfolio.quantity + actual_price * actual_qty
                portfolio.quantity += actual_qty
                portfolio.avg_cost = total_cost / portfolio.quantity
                portfolio.current_price = actual_price
                portfolio.market_value = actual_price * portfolio.quantity
                portfolio.unrealized_pnl = portfolio.market_value - float(portfolio.avg_cost) * portfolio.quantity
            else:
                portfolio = AgentPortfolio(
                    hire_id=signal.hire_id,
                    trader_id=signal.trader_id,
                    user_id=signal.user_id,
                    symbol=signal.symbol,
                    symbol_name=signal.symbol_name,
                    quantity=actual_qty,
                    avg_cost=actual_price,
                    current_price=actual_price,
                    market_value=actual_price * actual_qty,
                    unrealized_pnl=0,
                )
                db.add(portfolio)
        elif signal.action == "sell" and portfolio:
            if portfolio.quantity >= actual_qty:
                portfolio.quantity -= actual_qty
                if portfolio.quantity == 0:
                    await db.delete(portfolio)
                else:
                    portfolio.current_price = actual_price
                    portfolio.market_value = actual_price * portfolio.quantity
                    portfolio.unrealized_pnl = portfolio.market_value - float(portfolio.avg_cost) * portfolio.quantity
    else:
        logger.warning(f"确认信号无成交结果 user_id={current_user.id} signal_id={signal_id} symbol={signal.symbol}，不更新纸面持仓")

    response_data = {"success": True, "signal_id": signal_id, "message": "已确认执行"}
    if order_result is not None:
        response_data["order_id"] = order_result.id
        response_data["filled_price"] = order_result.filled_price
        response_data["filled_quantity"] = order_result.filled_quantity
    # 更新交易员统计数据
    await _update_trader_stats(db, signal.trader_id)

    return response_data




async def _update_trader_stats(db: AsyncSession, trader_id: str):
    """更新指定交易员的统计指标（信号确认后自动调用）"""
    from app.models.agent import AgentPerformance

    agent_result = await db.execute(
        select(AgentTrader).where(AgentTrader.id == trader_id)
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        return

    # total_trades: 已确认信号数
    trades_q = select(func.count(AgentSignal.id)).where(
        and_(
            AgentSignal.trader_id == trader_id,
            AgentSignal.exec_status == 'confirmed',
        )
    )
    total_trades = (await db.execute(trades_q)).scalar() or 0
    agent.total_trades = total_trades

    # 从 agent_performances 聚合指标
    perf_q = (
        select(AgentPerformance)
        .where(AgentPerformance.agent_id == trader_id)
        .order_by(AgentPerformance.period_end.desc())
        .limit(12)
    )
    perfs = (await db.execute(perf_q)).scalars().all()

    if perfs:
        win_rates = [float(p.win_rate) for p in perfs if p.win_rate is not None]
        if win_rates:
            agent.win_rate = round(sum(win_rates) / len(win_rates), 2)

        drawdowns = [float(p.max_drawdown) for p in perfs if p.max_drawdown is not None]
        if drawdowns:
            agent.max_drawdown = round(min(drawdowns), 2)

        sharpes = [float(p.sharpe_ratio) for p in perfs if p.sharpe_ratio is not None]
        if sharpes:
            agent.sharpe_ratio = round(sum(sharpes) / len(sharpes), 2)

    # annual_return: 从 salary_curve 计算年化收益
    salary_curve = agent.salary_curve or []
    if salary_curve and len(salary_curve) >= 2:
        first_value = float(salary_curve[0].get("value", 10000))
        last_value = float(salary_curve[-1].get("value", first_value))
        months = len(salary_curve)
        years = months / 12
        if years > 0 and first_value > 0:
            agent.annual_return = round((pow(last_value / 10000, 1 / years) - 1) * 100, 2)


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
        logger.warning(f"忽略信号失败: 信号不存在 user_id={current_user.id} signal_id={signal_id}")
        raise HTTPException(status_code=404, detail="信号不存在")
    if signal.exec_status != "pending":
        logger.warning(f"忽略信号失败: 状态为{signal.exec_status} user_id={current_user.id} signal_id={signal_id}")
        raise HTTPException(status_code=400, detail=f"信号状态为 {signal.exec_status}，无法忽略")

    signal.exec_status = "ignored"
    signal.updated_at = datetime.now(timezone.utc)
    logger.info(f"忽略信号 user_id={current_user.id} signal_id={signal_id}")
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


# ── 信号生成（支持 ai-hedge-fund 真实引擎 + mock fallback）──

@router.post("/{hire_id}/generate-signals", response_model=list[ConsoleSignalResponse])
async def generate_signals(
    hire_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    手动触发信号生成。
    如果 AI_HEDGE_FUND_ENABLED=true 且 OPENAI_API_KEY 已配置，使用真实引擎；
    否则 fallback 到模拟信号（保持 Phase 2 功能不变）。
    """
    hire = await _get_hire_or_404(db, hire_id, current_user.id)

    from app.engine import signal_generator as engine_sg

    result = await engine_sg.generate_signals(
        db=db,
        hire_id=hire_id,
        user_id=current_user.id,
    )

    generated = result.get("signals", [])

    # 构建响应
    signals = []
    for sig in generated:
        signals.append(ConsoleSignalResponse(
            id=sig.get("id", 0),
            hire_id=hire_id,
            trader_id=hire.agent_id,
            symbol=sig["symbol"],
            symbol_name=sig.get("name", sig["symbol"]),
            action=sig["action"],
            price=float(sig.get("price", 0)),
            quantity=sig.get("quantity", 100),
            confidence=sig.get("confidence", 50),
            reasoning=sig.get("reasoning", ""),
            exec_status="pending",
            created_at=sig.get("created_at", datetime.now(timezone.utc)),
        ))

    return signals


# ── 调度器状态 ──


# ── 调度器状态 ──

@router.get("/scheduler-status")
async def get_scheduler_status():
    """获取调度器运行状态"""
    from app.engine.scheduler_v2 import get_status
    return get_status()
