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
from datetime import datetime
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


@router.get("/account", response_model=AccountResponse)
async def get_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取账户信息（余额、市值、盈亏）"""
    info = await get_account_info(db, current_user)
    return {"success": True, "data": info}


@router.get("/positions", response_model=PositionListResponse)
async def get_positions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取持仓列表（实时市值）"""
    items, summary = await get_positions_summary(db, current_user)
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
        raise AppException(code="HOSTED_ACTIVE", message="AI托管已开启，手动交易已禁用。请先关闭AI托管再操作。", status_code=403)
    
    try:
        order = await place_order(db, current_user, req)
        return {"success": True, "data": order, "message": "下单成功"}
    except AppException:
        raise  # 让全局异常处理器处理
    except Exception as e:
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
        return {"success": True, "data": order, "message": "撤单成功"}
    except AppException:
        raise
    except Exception as e:
        raise AppException(code="CANCEL_FAILED", message=str(e), status_code=400)


@router.get("/analytics", response_model=PortfolioAnalyticsResponse)
async def get_analytics(
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
    analytics = await get_portfolio_analytics(db, current_user)
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
    收益率曲线
    
    基于账户初始资金 + 当前总资产计算。
    TODO: 未来接入历史每日快照后生成完整曲线。
    """
    from app.services.trading import INITIAL_BALANCE, get_or_create_account, get_positions
    account = await get_or_create_account(db, current_user)
    positions = await get_positions(db, current_user)
    total_market_value = sum(p.market_value for p in positions)
    total_equity = float(account.balance) + total_market_value
    
    today = datetime.now().strftime("%Y-%m-%d")
    points = [
        {"date": "start", "equity": INITIAL_BALANCE, "benchmark": INITIAL_BALANCE},
        {"date": today, "equity": round(total_equity, 2), "benchmark": round(total_equity, 2)},
    ]
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
    total_return = round(total_equity - INITIAL_BALANCE, 2)
    total_return_pct = round(total_return / INITIAL_BALANCE * 100, 4) if INITIAL_BALANCE > 0 else 0
    
    winning = [p for p in positions if p.profit > 0]
    win_rate = round(len(winning) / len(positions) * 100, 2) if positions else 0
    
    return {
        "success": True,
        "data": {
            "totalReturn": total_return_pct,
            "annualizedReturn": total_return_pct,
            "beatBenchmark": 0,
            "sharpeRatio": 0,
            "maxDrawdown": 0,
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
    
    # 最大回撤（简化为总收益跌幅，TODO：接入逐日追踪）
    max_drawdown = 0 if total_return >= 0 else round(abs(total_return) / INITIAL_BALANCE * 100, 2)
    
    return {
        "success": True,
        "data": {
            "winRate": win_rate,
            "profitLossRatio": profit_loss_ratio,
            "maxSingleProfit": round(max_profit, 2),
            "maxSingleLoss": round(max_loss, 2),
            "sharpeRatio": 0,
            "maxDrawdown": max_drawdown,
        },
    }


@router.post("/topup")
async def topup_account(
    amount: float = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """模拟充值 — 增加账户余额"""
    from sqlalchemy import select
    from app.models.trading import Account
    result = await db.execute(select(Account).where(Account.user_id == current_user.id))
    account = result.scalar_one_or_none()
    if not account:
        raise AppException(code="NO_ACCOUNT", message="账户不存在", status_code=404)
    account.balance += Decimal(str(amount))
    account.total_deposited += Decimal(str(amount))
    await db.commit()
    return {
        "success": True,
        "balance": account.balance,
        "topup_amount": amount,
        "message": f"成功充值 {amount} 元",
    }
