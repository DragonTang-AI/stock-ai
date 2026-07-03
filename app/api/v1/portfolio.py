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
)
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
