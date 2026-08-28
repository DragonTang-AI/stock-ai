import logging
"""
app/api/v1/portfolio.py — 交易路由（v1：纸面撮合）

端点：
- GET  /account      账户信息（余额/市值/盈亏）
- GET  /positions    持仓列表
- GET  /orders       订单列表
- POST /orders       下单（市价立即成交）
- DEL  /orders/{id}  撤单（v1 市价单已成交，返回错误）
- GET  /trades       成交记录

校验：
- 买入：余额 ≥ 金额 + 佣金
- 卖出：available ≥ 数量（T+1）
- 数量：100 的整数倍
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.engine.market_hours import is_market_hours
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.schemas.trading import (
    AccountResponse,
    PositionListResponse,
    OrderListResponse,
    OrderResponse,
    OrderRequest,
    TradeListResponse,
    PortfolioAnalyticsResponse,
    EquityCurveResponse,
    AttributionResponse,
    DashboardSummaryResponse,
    StatisticsResponse,
)
from decimal import Decimal
from datetime import datetime, timezone
from app.services.trading import (
    get_account_info,
    get_positions_summary,
    get_orders,
    place_order,
    cancel_order,
    get_trades,
    get_portfolio_analytics,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/account", response_model=AccountResponse)
async def get_account(
    market: str = Query("A"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取账户信息（余额、市值、盈亏）"""
    info = await get_account_info(db, current_user, market)
    return {"success": True, "data": info}


@router.get("/positions", response_model=PositionListResponse)
async def get_positions(
    market: str = Query("A"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取持仓列表（实时市值）"""
    items, summary = await get_positions_summary(db, current_user, market)
    return {"success": True, "data": items, "summary": summary}


@router.get("/orders", response_model=OrderListResponse)
async def get_orders_endpoint(
    status: Optional[str] = Query(None, description="过滤状态：pending/filled/canceled/rejected"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取订单列表"""
    items, total = await get_orders(db, current_user, status=status, limit=limit, offset=offset)
    return {"success": True, "data": items, "total": total}


@router.post("/orders", response_model=OrderResponse)
async def create_order(
    req: OrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    下单（市价立即成交）

    请求示例：
    ```json
    {
      "symbol": "600519.SH",
      "side": "buy",
      "quantity": 100,
      "order_type": "market"
    }
    ```

    校验：
    - 数量必须是 100 的整数倍
    - 买入：余额 ≥ 金额 + 佣金（万 2.5，最低 5 元）
    - 卖出：可卖数量 ≥ 数量（T+1：今日买入的股票下一交易日才能卖）
    """
    # AI托管开启时禁止手动下单
    from app.services.hosted_engine import engine as hosted_engine
    if hosted_engine.is_active(current_user.id):
        from app.core.exceptions import AppException
        logger.warning(f"手动下单被拒: AI托管开启 user_id={current_user.id} symbol={req.symbol}")
        raise AppException(code="HOSTED_ACTIVE", message="AI托管已开启，手动交易已禁用。请先关闭AI托管再操作。", status_code=403)

    if not is_market_hours():
        from app.core.exceptions import AppException
        logger.warning(f"手动下单被拒: 非交易时段 user_id={current_user.id} symbol={req.symbol}")
        raise AppException(code="NOT_TRADING_HOURS", message="当前非交易时段（A股：周一至周五 9:30-11:30, 13:00-15:00），无法下单", status_code=400)

    
    try:
        order = await place_order(db, current_user, req)
        logger.info(f"下单成功 user_id={current_user.id} symbol={req.symbol} side={req.side} qty={req.quantity} order_id={order.get('id') if isinstance(order, dict) else getattr(order, 'id', None)}")
        return {"success": True, "data": order, "message": "下单成功"}
    except AppException:
        logger.warning(f"下单失败 user_id={current_user.id} symbol={req.symbol} side={req.side}")
        raise  # 让全局异常处理器处理
    except Exception as e:
        logger.error(f"下单异常 user_id={current_user.id} symbol={req.symbol} error={e}")
        raise AppException(code="ORDER_FAILED", message=str(e), status_code=400)


@router.delete("/orders/{order_id}", response_model=OrderResponse)
async def delete_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    撤单（v1 市价单已立即成交，不允许撤单）
    """
    try:
        order = await cancel_order(db, current_user, order_id)
        logger.info(f"撤单成功 user_id={current_user.id} order_id={order_id}")
        return {"success": True, "data": order, "message": "撤单成功"}
    except AppException:
        logger.warning(f"撤单失败 user_id={current_user.id} order_id={order_id}")
        raise
    except Exception as e:
        logger.error(f"撤单异常 user_id={current_user.id} order_id={order_id} error={e}")
        raise AppException(code="CANCEL_FAILED", message=str(e), status_code=400)


@router.get("/analytics", response_model=PortfolioAnalyticsResponse)
async def get_analytics(
    market: str = Query("A"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    持仓分析

    返回：
    - position_count: 持仓数量
    - total_market_value: 持仓总市值
    - total_profit: 累计盈亏（含现金变动）
    - total_profit_pct: 累计收益率
    - daily_profit: 今日浮动盈亏（基于实时行情）
    - daily_profit_pct: 今日收益率
    - win_rate: 持仓胜率（盈利持仓占比）
    - best_position: 最佳持仓
    - worst_position: 最差持仓
    - top_holdings_concentration: Top3 持仓权重
    - top_holdings: Top3 持仓明细
    - holdings_distribution: 行业分布
    """
    analytics = await get_portfolio_analytics(db, current_user, market)
    return {"success": True, "data": analytics}


@router.get("/trades", response_model=TradeListResponse)
async def get_trades_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取成交记录"""
    items, total = await get_trades(db, current_user, limit=limit, offset=offset)
    return {"success": True, "data": items, "total": total}


@router.get("/equity_curve", response_model=EquityCurveResponse)
async def get_equity_curve(
    period: str = Query("1m", description="期限：1w/1m/3m/6m/1y/all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    收益率曲线（基于每日资产快照，含当前实时权益）

    数据源：
    - 历史点：equity_snapshots 每日快照（调度器 16:00-16:30 自动落库）
    - 最新点：实时计算（账户余额 + 持仓实时市值）
    - 基准：初始资金 10w 平线（V1 无指数基准数据，前端用收益% 展示）
    """
    from datetime import timedelta as _td
    from sqlalchemy import select as _select
    from app.models.trading import EquitySnapshot
    from app.services.trading import INITIAL_BALANCE, get_or_create_account, get_positions

    # 期限 → 起始日期
    today = datetime.now().date()
    period_days = {"1w": 7, "1m": 30, "3m": 90, "6m": 180, "1y": 365, "all": 3650}
    start_date = today - _td(days=period_days.get(period, 30))

    account = await get_or_create_account(db, current_user)
    positions = await get_positions(db, current_user)
    total_market_value = sum(p.market_value for p in positions)
    total_equity = float(account.balance) + total_market_value

    # 历史快照
    snap_rows = (await db.execute(
        _select(EquitySnapshot)
        .where(
            EquitySnapshot.user_id == current_user.id,
            EquitySnapshot.snapshot_date >= start_date,
        )
        .order_by(EquitySnapshot.snapshot_date)
    )).scalars().all()

    points = [
        {"date": "start", "equity": INITIAL_BALANCE, "benchmark": INITIAL_BALANCE}
    ]
    for s in snap_rows:
        points.append({
            "date": s.snapshot_date.strftime("%Y-%m-%d"),
            "equity": round(float(s.total_equity), 2),
            "benchmark": round(float(s.total_equity), 2),
        })
    # 去重最新日期，避免与实时点重复
    last_date = points[-1]["date"] if len(points) > 1 else None
    today_str = today.strftime("%Y-%m-%d")
    if last_date != today_str:
        points.append({
            "date": today_str,
            "equity": round(total_equity, 2),
            "benchmark": round(total_equity, 2),
        })
    return {"success": True, "data": points}


@router.get("/attribution", response_model=AttributionResponse)
async def get_attribution(
    period: str = Query("1m", description="期限：1w/1m/3m/6m/1y/all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """归因分析：各持仓盈亏贡献占比"""
    from app.services.trading import get_positions
    positions = await get_positions(db, current_user)
    if not positions:
        return {"success": True, "data": []}
    
    total_profit = sum(p.profit for p in positions)
    if total_profit == 0:
        return {"success": True, "data": [{"label": p.name, "contribution": 0, "percentage": 0} for p in positions]}
    
    items = [
        {
            "label": f"{p.name}({p.symbol})",
            "contribution": round(p.profit, 2),
            "percentage": round(abs(p.profit) / abs(total_profit) * 100, 2),
        }
        for p in sorted(positions, key=lambda x: abs(x.profit), reverse=True)
    ]
    return {"success": True, "data": items}


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """看板概览：总收益、年化收益、夏普比、最大回撤等"""
    from app.services.trading import INITIAL_BALANCE, get_or_create_account, get_positions
    account = await get_or_create_account(db, current_user)
    positions = await get_positions(db, current_user)

    total_market_value = sum(p.market_value for p in positions)
    total_equity = float(account.balance) + total_market_value
    total_deposited = float(account.total_deposited) if account.total_deposited else INITIAL_BALANCE
    total_return = round(total_equity - total_deposited, 2)
    total_return_pct = round(total_return / total_deposited * 100, 4) if total_deposited > 0 else 0

    # 年化收益：按账户创建天数年化
    annualized_return = total_return_pct
    if account.created_at:
        days = max((datetime.now(timezone.utc) - account.created_at).days, 1)
        annualized_return = round(total_return_pct / days * 365, 4)

    winning = [p for p in positions if p.profit > 0]
    win_rate = round(len(winning) / len(positions) * 100, 2) if positions else 0

    # 基于每日资产快照计算夏普比率与最大回撤（与 /statistics 同口径）
    from sqlalchemy import select as _sel
    from app.models.trading import EquitySnapshot
    snap_rows = (await db.execute(
        _sel(EquitySnapshot)
        .where(EquitySnapshot.user_id == current_user.id)
        .order_by(EquitySnapshot.snapshot_date)
    )).scalars().all()

    equity_seq = [float(s.total_equity) for s in snap_rows]
    equity_seq.append(total_equity)

    sharpe = 0.0
    max_drawdown = 0.0
    if len(equity_seq) >= 3:
        # 日收益率序列（简单相邻比）
        daily_rets = []
        for i in range(1, len(equity_seq)):
            prev = equity_seq[i - 1]
            if prev > 0:
                daily_rets.append(equity_seq[i] / prev - 1.0)
        if daily_rets:
            n = len(daily_rets)
            mean_r = sum(daily_rets) / n
            var_r = sum((r - mean_r) ** 2 for r in daily_rets) / n
            std_r = var_r ** 0.5
            if std_r > 1e-12:
                # 年化：A股约 250 交易日
                sharpe = round((mean_r / std_r) * (250 ** 0.5), 4)
            # 最大回撤：峰值回撤的最大值（百分比）
            peak = equity_seq[0]
            for v in equity_seq:
                if v > peak:
                    peak = v
                if peak > 0:
                    dd = (peak - v) / peak * 100.0
                    if dd > max_drawdown:
                        max_drawdown = dd
            max_drawdown = round(max_drawdown, 4)

    return {
        "success": True,
        "data": {
            "totalReturn": total_return_pct,
            "annualizedReturn": annualized_return,
            "beatBenchmark": 0,
            "sharpeRatio": sharpe,
            "maxDrawdown": max_drawdown,
            "winRate": win_rate,
        },
    }


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """统计指标：胜率、盈亏比、单笔最大盈亏、夏普比等"""
    from app.services.trading import INITIAL_BALANCE, get_or_create_account, get_positions, get_trades
    account = await get_or_create_account(db, current_user)
    positions = await get_positions(db, current_user)
    trades_list, _ = await get_trades(db, current_user)
    
    total_market_value = sum(p.market_value for p in positions)
    total_equity = float(account.balance) + total_market_value
    total_return = round(total_equity - INITIAL_BALANCE, 2)
    
    winning = [p for p in positions if p.profit > 0]
    losing = [p for p in positions if p.profit < 0]
    win_rate = round(len(winning) / len(positions) * 100, 2) if positions else 0
    
    # 盈亏比（平均盈利 / 平均亏损的绝对值）
    avg_win = sum(p.profit for p in winning) / len(winning) if winning else 0
    avg_loss = abs(sum(p.profit for p in losing)) / len(losing) if losing else 1
    profit_loss_ratio = round(avg_win / avg_loss, 2) if avg_loss > 0 else 0
    
    # 单只最大盈亏
    max_profit = max((p.profit for p in positions), default=0)
    max_loss = min((p.profit for p in positions), default=0)

    # ── 基于每日资产快照计算真实夏普比率与最大回撤 ──
    from sqlalchemy import select as _sel
    from app.models.trading import EquitySnapshot
    snap_rows = (await db.execute(
        _sel(EquitySnapshot)
        .where(EquitySnapshot.user_id == current_user.id)
        .order_by(EquitySnapshot.snapshot_date)
    )).scalars().all()

    equity_seq = [float(s.total_equity) for s in snap_rows]
    # 补上实时权益作为最新点
    equity_seq.append(total_equity)

    sharpe = 0.0
    max_drawdown = 0.0
    if len(equity_seq) >= 3:
        # 日收益率序列（简单相邻比）
        daily_rets = []
        for i in range(1, len(equity_seq)):
            prev = equity_seq[i - 1]
            if prev > 0:
                daily_rets.append(equity_seq[i] / prev - 1.0)
        if daily_rets:
            n = len(daily_rets)
            mean_r = sum(daily_rets) / n
            var_r = sum((r - mean_r) ** 2 for r in daily_rets) / n
            std_r = var_r ** 0.5
            if std_r > 1e-12:
                # 年化：A股约 250 交易日
                sharpe = round((mean_r / std_r) * (250 ** 0.5), 4)
            # 最大回撤：峰值回撤的最大值（百分比）
            peak = equity_seq[0]
            for v in equity_seq:
                if v > peak:
                    peak = v
                if peak > 0:
                    dd = (peak - v) / peak * 100.0
                    if dd > max_drawdown:
                        max_drawdown = dd
            max_drawdown = round(max_drawdown, 4)

    return {
        "success": True,
        "data": {
            "winRate": win_rate,
            "profitLossRatio": profit_loss_ratio,
            "maxSingleProfit": round(max_profit, 2),
            "maxSingleLoss": round(max_loss, 2),
            "sharpeRatio": sharpe,
            "maxDrawdown": max_drawdown,
        },
    }


@router.post("/topup")
async def topup_account(
    amount: float = Query(...),
    market: str = Query("A"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """模拟充值 — 增加账户余额（按市场账户充值）"""
    from sqlalchemy import select
    from app.models.trading import Account
    result = await db.execute(
        select(Account).where(
            Account.user_id == current_user.id,
            Account.market == market,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise AppException(code="NO_ACCOUNT", message="账户不存在", status_code=404)
    account.balance += Decimal(str(amount))
    account.total_deposited += Decimal(str(amount))
    await db.commit()
    currency = "HK$" if market == "HK" else "元"
    return {
        "success": True,
        "balance": account.balance,
        "topup_amount": amount,
        "message": f"成功充值 {amount} {currency}",
    }
