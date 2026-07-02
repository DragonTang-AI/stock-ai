"""
app.services.trading — 交易核心服务

v1 实现（纸面撮合）：
- 市价单：按当前市价立即成交
- 限价单：v1 暂不支持（直接当作市价单处理）
- 资金检查：买入时余额 ≥ 价格×数量 + 佣金
- 持仓检查：卖出时 available ≥ 卖出数量（T+1 校验）
- 佣金：万 2.5，最低 5 元
- 印花税：卖出千 1
- A 股交易单位 100 股
- T+1：当日买入的股票下一交易日才能卖

辅助方法：
- get_or_create_account：保证每个用户都有账户
- get_market_price：取实时市价（用 Sina 适配层）
- update_position：成交后更新持仓
- refresh_market_value：刷新持仓市值/盈亏
"""
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import select, update, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.user import User
from app.models.trading import Account, Order, Trade, Position
from app.schemas.trading import (
    AccountInfo,
    OrderRequest,
    PositionItem,
    OrderItem,
    TradeItem,
)
from app.services.market import fetch_realtime_quotes

logger = logging.getLogger(__name__)

# 交易费率
COMMISSION_RATE = 0.00025  # 万 2.5
COMMISSION_MIN = 5.0  # 最低 5 元
STAMP_TAX_SELL_RATE = 0.001  # 卖出印花税千 1
LOT_SIZE = 100  # A 股 1 手 = 100 股
INITIAL_BALANCE = 100000.0  # 初始资金


# ============== 账户 ==============
async def get_or_create_account(db: AsyncSession, user: User) -> Account:
    """获取或创建账户"""
    stmt = select(Account).where(Account.user_id == user.id)
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()
    if account is None:
        account = Account(
            user_id=user.id,
            balance=Decimal(str(INITIAL_BALANCE)),
            frozen=Decimal("0"),
            market="A",
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)
    return account


async def get_account_info(db: AsyncSession, user: User) -> AccountInfo:
    """获取账户信息（含市值/盈亏）"""
    account = await get_or_create_account(db, user)

    # 持仓市值
    positions = await get_positions(db, user)
    market_value = sum(p.market_value for p in positions)
    total_equity = float(account.balance) + float(account.frozen) + market_value
    profit = total_equity - INITIAL_BALANCE
    profit_pct = (profit / INITIAL_BALANCE) * 100 if INITIAL_BALANCE > 0 else 0.0

    return AccountInfo(
        account_id=account.id,
        balance=float(account.balance),
        frozen=float(account.frozen),
        total_equity=round(total_equity, 2),
        market_value=round(market_value, 2),
        profit=round(profit, 2),
        profit_pct=round(profit_pct, 4),
        market=account.market,
        created_at=account.created_at,
    )


# ============== 持仓 ==============
async def get_positions(db: AsyncSession, user: User) -> List[PositionItem]:
    """获取持仓列表（实时市值）"""
    stmt = (
        select(Position)
        .where(Position.user_id == user.id)
        .order_by(Position.market_value.desc())
    )
    result = await db.execute(stmt)
    positions = result.scalars().all()

    if not positions:
        return []

    # 批量取实时行情刷新市值
    symbols = [p.symbol for p in positions]
    try:
        quotes = await fetch_realtime_quotes(symbols)
        quote_map = {q.symbol: q for q in quotes}
    except Exception as e:
        logger.warning(f"刷新持仓市值失败，使用上次记录的价格: {e}")
        quote_map = {}

    items = []
    for p in positions:
        q = quote_map.get(p.symbol)
        if q and q.price > 0:
            market_price = q.price
            market_value = market_price * p.quantity
            cost_amount = float(p.cost_price) * p.quantity
            profit = market_value - cost_amount
            profit_pct = (profit / cost_amount * 100) if cost_amount > 0 else 0.0
            # 同步到 DB（轻量更新）
            p.market_price = Decimal(str(market_price))
            p.market_value = Decimal(str(market_value))
            p.profit = Decimal(str(profit))
            p.profit_pct = Decimal(str(profit_pct))
        else:
            market_price = float(p.market_price)
            market_value = float(p.market_value)
            profit = float(p.profit)
            profit_pct = float(p.profit_pct)

        items.append(PositionItem(
            symbol=p.symbol,
            name=p.name,
            market=p.market,
            quantity=p.quantity,
            available=p.available,
            cost_price=float(p.cost_price),
            cost_amount=round(float(p.cost_price) * p.quantity, 2),
            market_price=round(market_price, 4),
            market_value=round(market_value, 2),
            profit=round(profit, 2),
            profit_pct=round(profit_pct, 4),
            updated_at=p.updated_at,
        ))

    # 批量 commit 刷新后的价格
    try:
        await db.commit()
    except Exception as e:
        logger.warning(f"持仓价格刷新 commit 失败: {e}")
        await db.rollback()

    return items


async def get_positions_summary(db: AsyncSession, user: User) -> Tuple[List[PositionItem], dict]:
    """获取持仓列表 + 汇总"""
    items = await get_positions(db, user)
    summary = {
        "total_market_value": round(sum(p.market_value for p in items), 2),
        "total_profit": round(sum(p.profit for p in items), 2),
        "total_cost": round(sum(p.cost_amount for p in items), 2),
        "total_profit_pct": 0.0,
    }
    if summary["total_cost"] > 0:
        summary["total_profit_pct"] = round(summary["total_profit"] / summary["total_cost"] * 100, 4)
    return items, summary


# ============== 撮合（下单） ==============
async def place_order(db: AsyncSession, user: User, req: OrderRequest) -> OrderItem:
    """
    下单（v1：市价立即成交）

    流程：
    1. 获取/创建账户
    2. 取实时市价
    3. 校验：
       - 买入：余额 ≥ 金额 + 佣金
       - 卖出：available ≥ 数量（T+1 校验）
    4. 扣/加资金，更新持仓，写 Trade
    5. 更新 Order 状态为 filled
    """
    account = await get_or_create_account(db, user)

    # 1. 取市价
    symbol = req.symbol.upper()
    try:
        quotes = await fetch_realtime_quotes([symbol])
    except Exception as e:
        raise AppException(code="QUOTE_FAILED", message=f"获取行情失败: {e}", status_code=502)
    if not quotes:
        raise AppException(code="SYMBOL_NOT_FOUND", message=f"未找到股票 {symbol} 的行情", status_code=404)
    quote = quotes[0]

    # 限价单：v1 简化处理为市价（实际应等待价格触及）
    fill_price = float(quote.price) if req.order_type == "market" else (req.price or float(quote.price))
    if fill_price <= 0:
        raise AppException(code="INVALID_PRICE", message=f"成交价无效: {fill_price}", status_code=400)

    quantity = req.quantity
    amount = fill_price * quantity
    commission = max(amount * COMMISSION_RATE, COMMISSION_MIN)
    tax = amount * STAMP_TAX_SELL_RATE if req.side == "sell" else 0.0
    total_cost = amount + commission + tax  # 买入实际扣款 / 卖出实际收款 = amount - commission - tax

    # 2. 校验
    if req.side == "buy":
        if float(account.balance) < total_cost:
            raise AppException(
                code="INSUFFICIENT_BALANCE",
                message=f"余额不足：需要 {total_cost:.2f} 元（金额 {amount:.2f} + 佣金 {commission:.2f}），"
                f"可用 {float(account.balance):.2f} 元",
                status_code=400,
            )
    else:  # sell
        # T+1 校验：检查持仓可用数量
        pos_stmt = select(Position).where(
            Position.user_id == user.id,
            Position.symbol == symbol,
        )
        pos_result = await db.execute(pos_stmt)
        position = pos_result.scalar_one_or_none()
        if position is None:
            raise AppException(code="NO_POSITION", message=f"未持有 {symbol}，无法卖出", status_code=400)
        if position.available < quantity:
            raise AppException(
                code="INSUFFICIENT_AVAILABLE",
                message=f"可卖数量不足：需要 {quantity}，可用 {position.available}（T+1 限制：今日买入的股票下一交易日才能卖）",
                status_code=400,
            )

    # 3. 写订单
    order = Order(
        user_id=user.id,
        account_id=account.id,
        symbol=symbol,
        name=quote.name or "",
        side=req.side,
        order_type=req.order_type,
        price=Decimal(str(fill_price)),
        quantity=quantity,
        filled_quantity=quantity,
        filled_price=Decimal(str(fill_price)),
        amount=Decimal(str(amount)),
        commission=Decimal(str(commission)),
        tax=Decimal(str(tax)),
        status="filled",
        filled_at=datetime.now(timezone.utc),
    )
    db.add(order)
    await db.flush()  # 拿到 order.id

    # 4. 扣/加资金
    if req.side == "buy":
        account.balance = account.balance - Decimal(str(total_cost))
    else:
        account.balance = account.balance + Decimal(str(amount - commission - tax))

    # 5. 写成交记录
    trade = Trade(
        user_id=user.id,
        account_id=account.id,
        order_id=order.id,
        symbol=symbol,
        name=quote.name or "",
        side=req.side,
        price=Decimal(str(fill_price)),
        quantity=quantity,
        amount=Decimal(str(amount)),
        commission=Decimal(str(commission)),
        tax=Decimal(str(tax)),
        trade_date=date.today(),
    )
    db.add(trade)

    # 6. 更新持仓
    await _update_position(db, user.id, account.id, symbol, quote.name or "", req.side, fill_price, quantity)

    await db.commit()
    await db.refresh(order)

    return OrderItem(
        id=order.id,
        user_id=order.user_id,
        account_id=order.account_id,
        symbol=order.symbol,
        name=order.name,
        side=order.side,
        order_type=order.order_type,
        price=float(order.price),
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        filled_price=float(order.filled_price),
        amount=float(order.amount),
        commission=float(order.commission),
        tax=float(order.tax),
        status=order.status,
        reject_reason=order.reject_reason,
        created_at=order.created_at,
        filled_at=order.filled_at,
        canceled_at=order.canceled_at,
    )


async def _update_position(
    db: AsyncSession,
    user_id: int,
    account_id: int,
    symbol: str,
    name: str,
    side: str,
    price: float,
    quantity: int,
) -> None:
    """更新持仓（内部）"""
    stmt = select(Position).where(
        Position.user_id == user_id,
        Position.symbol == symbol,
    )
    result = await db.execute(stmt)
    position = result.scalar_one_or_none()

    if side == "buy":
        if position is None:
            position = Position(
                user_id=user_id,
                account_id=account_id,
                symbol=symbol,
                name=name,
                market="A",
                quantity=quantity,
                available=0,  # T+1：今日买入不可卖
                cost_price=Decimal(str(price)),
                cost_amount=Decimal(str(price * quantity)),
                market_price=Decimal(str(price)),
                market_value=Decimal(str(price * quantity)),
            )
            db.add(position)
        else:
            # 加权平均成本
            total_cost = float(position.cost_price) * position.quantity + price * quantity
            new_qty = position.quantity + quantity
            new_cost_price = total_cost / new_qty if new_qty > 0 else price
            position.quantity = new_qty
            position.cost_price = Decimal(str(new_cost_price))
            position.cost_amount = Decimal(str(total_cost))
            # market_price / market_value 会在 get_positions 刷新
    else:  # sell
        if position is None:
            raise AppException(code="NO_POSITION", message=f"未持有 {symbol}", status_code=400)
        position.quantity -= quantity
        # 可用数量已经在 place_order 校验过，这里直接扣
        position.available = max(0, position.available - quantity)
        if position.quantity == 0:
            # 清仓：删除持仓行
            await db.delete(position)
        else:
            # cost_amount 按比例扣减
            cost_amount = float(position.cost_price) * position.quantity
            position.cost_amount = Decimal(str(cost_amount))


# ============== 订单查询 ==============
async def get_orders(
    db: AsyncSession,
    user: User,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[OrderItem], int]:
    """获取订单列表"""
    base = select(Order).where(Order.user_id == user.id)
    if status:
        base = base.where(Order.status == status)
    total_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_stmt)).scalar() or 0

    stmt = base.order_by(Order.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    orders = result.scalars().all()

    items = [
        OrderItem(
            id=o.id,
            user_id=o.user_id,
            account_id=o.account_id,
            symbol=o.symbol,
            name=o.name,
            side=o.side,
            order_type=o.order_type,
            price=float(o.price),
            quantity=o.quantity,
            filled_quantity=o.filled_quantity,
            filled_price=float(o.filled_price),
            amount=float(o.amount),
            commission=float(o.commission),
            tax=float(o.tax),
            status=o.status,
            reject_reason=o.reject_reason,
            created_at=o.created_at,
            filled_at=o.filled_at,
            canceled_at=o.canceled_at,
        )
        for o in orders
    ]
    return items, total


async def cancel_order(db: AsyncSession, user: User, order_id: int) -> OrderItem:
    """撤单（v1：市价单已立即成交，不允许撤单；返回错误）"""
    stmt = select(Order).where(
        Order.id == order_id,
        Order.user_id == user.id,
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if order is None:
        raise AppException(code="ORDER_NOT_FOUND", message=f"订单 {order_id} 不存在", status_code=404)
    if order.status != "pending":
        raise AppException(code="ORDER_NOT_CANCELLABLE", message=f"订单 {order_id} 状态为 {order.status}，不能撤单（市价单已立即成交）", status_code=400)
    # v1 不支持 pending 订单（无撮合循环），理论上不会进入这里
    order.status = "canceled"
    order.canceled_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(order)
    return OrderItem(
        id=order.id,
        user_id=order.user_id,
        account_id=order.account_id,
        symbol=order.symbol,
        name=order.name,
        side=order.side,
        order_type=order.order_type,
        price=float(order.price),
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        filled_price=float(order.filled_price),
        amount=float(order.amount),
        commission=float(order.commission),
        tax=float(order.tax),
        status=order.status,
        reject_reason=order.reject_reason,
        created_at=order.created_at,
        filled_at=order.filled_at,
        canceled_at=order.canceled_at,
    )


# ============== 成交 ==============
async def get_trades(
    db: AsyncSession,
    user: User,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[TradeItem], int]:
    """获取成交记录"""
    base = select(Trade).where(Trade.user_id == user.id)
    total_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_stmt)).scalar() or 0

    stmt = base.order_by(Trade.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    trades = result.scalars().all()

    items = [
        TradeItem(
            id=t.id,
            order_id=t.order_id,
            symbol=t.symbol,
            name=t.name,
            side=t.side,
            price=float(t.price),
            quantity=t.quantity,
            amount=float(t.amount),
            commission=float(t.commission),
            tax=float(t.tax),
            trade_date=t.trade_date,
            created_at=t.created_at,
        )
        for t in trades
    ]
    return items, total
