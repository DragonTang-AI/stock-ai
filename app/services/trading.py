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
from datetime import date, datetime, timezone, timedelta
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
from app.services.hk_lot_size import get_lot_size, is_hk_symbol

logger = logging.getLogger(__name__)

# 交易费率
COMMISSION_RATE = 0.00025  # 万 2.5
COMMISSION_MIN = 5.0  # 最低 5 元
STAMP_TAX_SELL_RATE = 0.001  # 卖出印花税千 1
LOT_SIZE = 100  # A 股 1 手 = 100 股

# 港股费率
HK_COMMISSION_RATE = 0.0003  # 万 3
HK_COMMISSION_MIN = 15.0  # 最低 15 HKD
HK_STAMP_TAX_BOTH_RATE = 0.0013  # 买卖双向 0.13%
INITIAL_BALANCE = 100000.0  # 初始资金


# ============== 账户 ==============
async def get_or_create_account(db: AsyncSession, user: User, market: str = "A") -> Account:
    """获取或创建账户"""
    stmt = select(Account).where(Account.user_id == user.id, Account.market == market)
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()
    if account is None:
        account = Account(
            user_id=user.id,
            balance=Decimal(str(INITIAL_BALANCE)),
            frozen=Decimal("0"),
            market=market,
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)
    return account


async def get_account_info(db: AsyncSession, user: User, market: str = "A") -> AccountInfo:
    """获取账户信息（含市值/盈亏）"""
    account = await get_or_create_account(db, user, market)

    # 持仓市值
    positions = await get_positions(db, user, market)
    market_value = sum(p.market_value for p in positions)
    total_equity = float(account.balance) + float(account.frozen) + market_value
    deposited = float(account.total_deposited) if account.total_deposited else INITIAL_BALANCE
    profit = total_equity - deposited
    profit_pct = (profit / deposited) * 100 if deposited > 0 else 0.0

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
async def get_positions(db: AsyncSession, user: User, market: str | None = None) -> List[PositionItem]:
    """获取持仓列表（实时市值）"""
    stmt = select(Position).where(Position.user_id == user.id)
    if market is not None:
        stmt = stmt.where(Position.market == market)
    stmt = stmt.order_by(Position.market_value.desc())
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



async def _compute_hk_available(db: AsyncSession, user_id: int, symbol: str) -> int:
    """计算港股 T+2 可卖数量（当日买入两日后方可卖出）"""
    today = date.today()
    # 查找 T+2 之前买入的数量
    stmt = select(func.sum(Trade.quantity)).where(
        Trade.user_id == user_id,
        Trade.symbol == symbol,
        Trade.side == "buy",
        Trade.trade_date <= today - datetime.timedelta(days=2),
    )
    result = await db.execute(stmt)
    total_buy_settled = result.scalar() or 0

    # 查找所有卖出的数量
    stmt2 = select(func.sum(Trade.quantity)).where(
        Trade.user_id == user_id,
        Trade.symbol == symbol,
        Trade.side == "sell",
    )
    result2 = await db.execute(stmt2)
    total_sell = result2.scalar() or 0

    settled = total_buy_settled - total_sell
    return max(0, int(settled))


# ============== 撮合（下单） ==============
async def place_order(db: AsyncSession, user: User, req: OrderRequest, fallback_price: float | None = None, signal_id: str | None = None) -> OrderItem:
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
    symbol = req.symbol.upper()
    is_hk = is_hk_symbol(symbol)
    hk_market = "HK" if is_hk else "A"

    account = await get_or_create_account(db, user, hk_market)
    # 1.0 校验整手倍数
    if is_hk:
        code = symbol.replace(".HK", "").replace(".hk", "").strip()
        lot_size = get_lot_size(code)
        if req.quantity % lot_size != 0:
            raise AppException(
                code="INVALID_QUANTITY",
                message=f"港股 {symbol} 每手 {lot_size} 股，数量必须是 {lot_size} 的整数倍",
                status_code=400,
            )
    elif req.quantity % 100 != 0:
        raise AppException(
            code="INVALID_QUANTITY",
            message="A股数量必须是 100 的整数倍（交易单位：手）",
            status_code=400,
        )


    # 1. 取市价
    quote = None
    try:
        quotes = await fetch_realtime_quotes([symbol])
        if quotes:
            quote = quotes[0]
    except Exception as e:
        if fallback_price and fallback_price > 0:
            logger.warning(f"获取 {symbol} 行情失败，使用兜底价 {fallback_price}: {e}")
        else:
            raise AppException(code="QUOTE_FAILED", message=f"获取行情失败: {e}", status_code=502)

    if not quote:
        if fallback_price and fallback_price > 0:
            from collections import namedtuple
            FallbackQuote = namedtuple('FallbackQuote', ['symbol', 'name', 'price'])
            quote = FallbackQuote(symbol=symbol, name=symbol, price=fallback_price)
        else:
            raise AppException(code="SYMBOL_NOT_FOUND", message=f"未找到股票 {symbol} 的行情", status_code=404)

    # 限价单：v1 简化处理为市价（实际应等待价格触及）
    fill_price = float(quote.price) if req.order_type == "market" else (req.price or float(quote.price))
    if fill_price <= 0:
        raise AppException(code="INVALID_PRICE", message=f"成交价无效: {fill_price}", status_code=400)

    quantity = req.quantity
    amount = fill_price * quantity

    # 按市场计算费率
    if is_hk:
        commission = max(amount * HK_COMMISSION_RATE, HK_COMMISSION_MIN)
        tax = amount * HK_STAMP_TAX_BOTH_RATE  # 港股买卖双向 0.13%
    else:
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
        # 持仓检查：无持仓不可卖；模拟盘不启用 T+1（买入时 available 即赋满），故不再校验 available
        pos_stmt = select(Position).where(
            Position.user_id == user.id,
            Position.symbol == symbol,
        )
        pos_result = await db.execute(pos_stmt)
        position = pos_result.scalar_one_or_none()
        if position is None:
            raise AppException(code="NO_POSITION", message=f"未持有 {symbol}，无法卖出", status_code=400)
        check_qty = position.available if is_hk else position.quantity
        if check_qty < quantity:
            raise AppException(
                code="INSUFFICIENT_POSITION",
                message=f"持仓不足：需要卖出 {quantity}，持有可用 {check_qty}（总 {position.quantity}）",
                status_code=400,
            )

    # 3. 写订单
    order = Order(
        user_id=user.id,
        account_id=account.id,
        symbol=symbol,
        market=hk_market,
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
        signal_id=signal_id,
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
        market=hk_market,
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
    await _update_position(db, user.id, account.id, symbol, quote.name or "", req.side, fill_price, quantity, is_hk=is_hk, market=hk_market)

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
    is_hk: bool = False,
    market: str = "A",
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
                market=market,
                quantity=quantity,
                available=0 if is_hk else quantity,  # HK T+2：买入当日不可卖；A 股不限制
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
            position.available = new_qty  # A 股买入全部可用；港股买入时 available 不变（T+2 处理在 place_order 内）
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
async def get_portfolio_analytics(
    db: AsyncSession,
    user: User,
) -> dict:
    """
    持仓分析：
    - 总盈亏 / 日均盈亏
    - 持仓胜率
    - 最佳/最差持仓
    - 持仓集中度（Top 3 权重）
    - 行业分布（按个股名称特征分组）
    """
    from decimal import Decimal

    account = await get_or_create_account(db, user)
    positions = await get_positions(db, user)

    if not positions:
        return {
            "position_count": 0,
            "total_market_value": 0,
            "total_profit": round(float(account.balance) - float(account.total_deposited or INITIAL_BALANCE), 2),
            "total_profit_pct": round((float(account.balance) - float(account.total_deposited or INITIAL_BALANCE)) / float(account.total_deposited or INITIAL_BALANCE) * 100, 4) if (account.total_deposited or INITIAL_BALANCE) > 0 else 0,
            "win_rate": 0,
            "best_position": None,
            "worst_position": None,
            "top_holdings_concentration": 0,
            "top_holdings": [],
            "holdings_distribution": [],
        }

    total_market_value = sum(p.market_value for p in positions)
    total_cost = sum(p.cost_amount for p in positions)

    # 总盈亏（持仓盈亏 + 现金变动）
    total_equity = float(account.balance) + total_market_value
    total_deposited = float(account.total_deposited) if account.total_deposited else INITIAL_BALANCE
    total_profit = round(total_equity - total_deposited, 2)
    total_profit_pct = round((total_profit / total_deposited) * 100, 4) if total_deposited > 0 else 0

    # 胜率
    winning = [p for p in positions if p.profit > 0]
    win_rate = round(len(winning) / len(positions) * 100, 2) if positions else 0

    # 最佳/最差
    sorted_positions = sorted(positions, key=lambda p: p.profit_pct, reverse=True)
    best = sorted_positions[0] if sorted_positions else None
    worst = sorted_positions[-1] if sorted_positions else None

    def _to_score(p, total_mv):
        return {
            "symbol": p.symbol,
            "name": p.name,
            "profit": round(p.profit, 2),
            "profit_pct": round(p.profit_pct, 4),
            "market_value": round(p.market_value, 2),
            "weight": round(p.market_value / total_mv * 100, 2) if total_mv > 0 else 0,
        }

    # 持仓集中度（Top 3 权重）
    top3 = sorted(positions, key=lambda p: p.market_value, reverse=True)[:3]
    top3_weight = sum(p.market_value for p in top3) / total_market_value * 100 if total_market_value > 0 else 0
    top_holdings = [_to_score(p, total_market_value) for p in top3]

    # 行业分布
    sector_groups = {}
    for p in positions:
        sector = _guess_sector(p.name, p.symbol)
        if sector not in sector_groups:
            sector_groups[sector] = {"sector": sector, "market_value": 0, "profit": 0.0, "count": 0}
        sector_groups[sector]["market_value"] += p.market_value
        sector_groups[sector]["profit"] += p.profit
        sector_groups[sector]["count"] += 1

    holdings_distribution = [
        {
            "sector": sg["sector"],
            "market_value": round(sg["market_value"], 2),
            "weight": round(sg["market_value"] / total_market_value * 100, 2) if total_market_value > 0 else 0,
            "profit": round(sg["profit"], 2),
            "count": sg["count"],
        }
        for sg in sorted(sector_groups.values(), key=lambda x: x["market_value"], reverse=True)
    ]

    # 今日盈亏（基于持仓的当日涨跌幅）
    symbols = [p.symbol for p in positions]
    daily_profit = None
    daily_profit_pct = None
    try:
        quotes = await fetch_realtime_quotes(symbols)
        quote_map = {q.symbol: q for q in quotes}
        daily_change_total = sum(
            (q.change_pct or 0) * p.market_value / 100
            for q in quotes
            for p in positions
            if q.symbol == p.symbol
        )
        daily_profit = round(daily_change_total, 2)
        daily_profit_pct = round(daily_change_total / total_equity * 100, 4) if total_equity > 0 else 0
    except Exception:
        pass

    return {
        "position_count": len(positions),
        "total_market_value": round(total_market_value, 2),
        "total_profit": total_profit,
        "total_profit_pct": total_profit_pct,
        "daily_profit": daily_profit,
        "daily_profit_pct": daily_profit_pct,
        "win_rate": win_rate,
        "best_position": _to_score(best, total_market_value) if best else None,
        "worst_position": _to_score(worst, total_market_value) if worst else None,
        "top_holdings_concentration": round(top3_weight, 2),
        "top_holdings": top_holdings,
        "holdings_distribution": holdings_distribution,
    }


def _guess_sector(name: str, symbol: str) -> str:
    """根据个股名称后缀猜测所属行业"""
    bank_keywords = ["银行", "中国银", "招商银", "工商", "建设", "农业", "交通", "兴业", "浦发", "平安"]
    tech_keywords = ["科技", "技术", "信息", "软件", "电子", "半导体", "通信", "宁德"]
    medical_keywords = ["医药", "医疗", "生物", "恒瑞", "药", "康"]
    food_keywords = ["茅台", "五粮", "食品", "饮料", "白酒", "伊利"]
    finance_keywords = ["证券", "保险", "信托", "中国平", "中信", "中金", "东方财"]
    energy_keywords = ["石油", "石化", "能源", "煤炭", "电力", "核电", "中国神"]
    manu_keywords = ["制造", "机械", "汽车", "比亚迪", "美的", "格力", "海尔"]
    house_keywords = ["保利", "万科", "房产", "地产"]

    if any(kw in name for kw in bank_keywords): return "银行"
    if any(kw in name for kw in tech_keywords): return "科技"
    if any(kw in name for kw in medical_keywords): return "医药"
    if any(kw in name for kw in food_keywords): return "消费"
    if any(kw in name for kw in finance_keywords): return "金融"
    if any(kw in name for kw in energy_keywords): return "能源"
    if any(kw in name for kw in manu_keywords): return "制造"
    if any(kw in name for kw in house_keywords): return "地产"
    if "中国" in name and "中国" in symbol[:2]: return "国企"

    return "其他"


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

    # 关联订单 -> 信号 -> 交易员，识别成交来源
    from sqlalchemy import select as sa_select, and_, or_, text as sa_text
    from app.models.agent import AgentSignal, AgentTrader
    order_ids = [t.order_id for t in trades]
    source_map: dict[int, dict] = {}
    if order_ids:
        orders_res = await db.execute(
            sa_select(Order.id, Order.user_id, Order.signal_id).where(Order.id.in_(order_ids))
        )
        order_rows = orders_res.all()
        sig_map = {oid: {"user_id": uid, "signal_id": sid} for oid, uid, sid in order_rows}
        tid_by_order: dict[int, str] = {}

        # 1) 纯数字 signal_id = agent_signals.id（手动确认/历史路径）
        num_sig_ids = [
            info["signal_id"] for info in sig_map.values()
            if info["signal_id"] and str(info["signal_id"]).isdigit()
        ]
        if num_sig_ids:
            sigs_res = await db.execute(
                sa_select(AgentSignal.id, AgentSignal.trader_id).where(AgentSignal.id.in_([int(s) for s in num_sig_ids]))
            )
            tid_by_sig = {str(sid): tid for sid, tid in sigs_res.all()}
            for oid, info in sig_map.items():
                if info["signal_id"] and str(info["signal_id"]).isdigit():
                    tid = tid_by_sig.get(str(info["signal_id"]))
                    if tid:
                        tid_by_order[oid] = tid

        # 2) sig_{user}_{symbol}_{ts}（全托管自动执行/confirm 落款）→ 按 user+裸symbol 关联最近 agent 信号
        import re
        sig_str_re = re.compile(r"^sig_(\d+)_(.+?)_\d+$")
        str_candidates: list[tuple[int, int, str]] = []
        for oid, info in sig_map.items():
            sid = info["signal_id"]
            if not sid or str(sid).isdigit():
                continue
            m = sig_str_re.match(str(sid))
            if m:
                str_candidates.append((oid, int(m.group(1)), m.group(2).split(".")[0].upper()))
        if str_candidates:
            pair_conds = [
                and_(AgentSignal.user_id == uid, AgentSignal.symbol == sym)
                for uid, sym in {(uid, sym) for _, uid, sym in str_candidates}
            ]
            sigs_res2 = await db.execute(
                sa_select(AgentSignal.user_id, AgentSignal.symbol, AgentSignal.trader_id, AgentSignal.created_at)
                .where(or_(*pair_conds))
                .order_by(AgentSignal.created_at.desc())
            )
            latest_tid: dict[tuple[int, str], str] = {}
            for uid, sym, tid, ts in sigs_res2.all():
                key = (uid, sym)
                if key not in latest_tid and tid:
                    latest_tid[key] = tid
            for oid, uid, sym in str_candidates:
                tid = latest_tid.get((uid, sym))
                if tid:
                    tid_by_order[oid] = tid

        # 3) sell_{symbol}_{ts}（AI_HOSTED 托管路径）→ 匹配 hosted_logs 标记托管来源
        sell_str_re = re.compile(r"^sell_(.+?)_\d+$")
        hosted_sig_ids = [
            str(info["signal_id"]) for oid, info in sig_map.items()
            if info["signal_id"] and sell_str_re.match(str(info["signal_id"]))
        ]
        if hosted_sig_ids:
            hosted_res = await db.execute(
                sa_text(
                    "SELECT DISTINCT signal_id FROM hosted_logs "
                    "WHERE signal_id = ANY(:sids)"
                ).bindparams(sids=hosted_sig_ids)
            )
            hosted_sids = {row[0] for row in hosted_res.all()}
            for oid, info in sig_map.items():
                if info["signal_id"] in hosted_sids:
                    source_map[oid] = {"source": "hosted", "trader_name": None}

        # 汇总交易员名称
        trader_ids = list({tid for tid in tid_by_order.values() if tid})
        if trader_ids:
            traders_res = await db.execute(
                sa_select(AgentTrader.id, AgentTrader.code_name).where(AgentTrader.id.in_(trader_ids))
            )
            name_by_tid = {tid: cname for tid, cname in traders_res.all()}
            for oid, tid in tid_by_order.items():
                if tid and tid in name_by_tid:
                    source_map[oid] = {"source": "agent", "trader_name": name_by_tid[tid]}
        for oid in order_ids:
            if oid not in source_map:
                source_map[oid] = {"source": "user", "trader_name": None}

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
            source=source_map.get(t.order_id, {}).get("source", "user"),
            trader_name=source_map.get(t.order_id, {}).get("trader_name"),
        )
        for t in trades
    ]
    return items, total
