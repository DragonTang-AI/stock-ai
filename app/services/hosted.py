"""P1-F3: AI托管核心服务"""
from __future__ import annotations
import logging
from datetime import datetime, timezone, date
from decimal import Decimal
import uuid
import hashlib
from typing import Optional, Tuple
from sqlalchemy import select, text, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.config_compliance import compliance_settings
from app.models.user import User
from app.models.trading import Account, Order, Position
from app.schemas.hosted import (
    HostedMode, HostedStatusResponse, HostedLogItem, HostedConfigRequest,
)
from app.middleware.audit import audit_log, AUDIT_COMPLIANCE_FLAG

logger = logging.getLogger(__name__)

# 费率
LOT_SIZE = 100
COMMISSION_RATE = 0.00025
COMMISSION_MIN = 5.0
STAMP_TAX_SELL_RATE = 0.001


# ─────────────────────────────────────────────────────────
# SQL 辅助
# ─────────────────────────────────────────────────────────
def _text(q: str):
    return text(q)


async def _get_hosted_settings(db: AsyncSession, user_id: int) -> Optional[dict]:
    """读取托管设置（无则返回 None）"""
    result = await db.execute(
        _text(
            "SELECT id, mode, enabled_at, disabled_at, max_position_ratio, "
            "max_single_trade_ratio, min_confidence FROM public.hosted_settings "
            "WHERE user_id = :uid"
        ),
        {"uid": user_id},
    )
    row = result.fetchone()
    if row is None:
        return None
    return {
        "id": str(row[0]),
        "mode": row[1],
        "enabled_at": row[2],
        "disabled_at": row[3],
        "max_position_ratio": row[4],
        "max_single_trade_ratio": row[5],
        "min_confidence": row[6],
    }


async def _upsert_hosted_settings(
    db: AsyncSession,
    user_id: int,
    mode: HostedMode,
    config: Optional[HostedConfigRequest] = None,
) -> dict:
    """插入或更新托管设置"""
    now = datetime.now(timezone.utc)
    settings = await _get_hosted_settings(db, user_id)
    
    max_pos = config.max_position_ratio if config else None
    max_trade = config.max_single_trade_ratio if config else None
    min_conf = config.min_confidence if config else None
    enabled_at = now if mode == HostedMode.AI_HOSTED else None
    disabled_at = now if mode == HostedMode.MANUAL else None

    if settings:
        # UPDATE
        stmt = _text(
            "UPDATE public.hosted_settings SET "
            "mode = :mode, enabled_at = :ena, disabled_at = :dis, "
            "max_position_ratio = :mpr, max_single_trade_ratio = :mstr, "
            "min_confidence = :mc, updated_at = NOW() "
            "WHERE user_id = :uid"
        )
        await db.execute(stmt, {
            "mode": mode.value, "ena": enabled_at, "dis": disabled_at,
            "mpr": max_pos, "mstr": max_trade, "mc": min_conf, "uid": user_id,
        })
    else:
        # INSERT
        stmt = _text(
            "INSERT INTO public.hosted_settings "
            "(user_id, mode, enabled_at, max_position_ratio, max_single_trade_ratio, min_confidence) "
            "VALUES (:uid, :mode, :ena, :mpr, :mstr, :mc)"
        )
        await db.execute(stmt, {
            "uid": user_id, "mode": mode.value, "ena": enabled_at,
            "mpr": max_pos, "mstr": max_trade, "mc": min_conf,
        })
    await db.commit()
    return await _get_hosted_settings(db, user_id)


async def _log_hosted(
    db: AsyncSession,
    user_id: int,
    signal_id: Optional[str],
    order_id: Optional[int],
    action: str,
    symbol: str,
    target_price: Optional[float],
    qty: Optional[int],
    status: str,
    reason: str,
):
    """记录托管日志"""
    reason_escaped = reason.replace("'", "''")[:500]
    # Convert string signal_id to UUID
    sid_uuid = None
    if signal_id:
        try:
            import uuid as _uuid
            sid_uuid = str(_uuid.UUID(signal_id))
        except (ValueError, TypeError):
            sid_uuid = str(_uuid.uuid5(_uuid.NAMESPACE_DNS, signal_id))
    
    await db.execute(
        _text(
            "INSERT INTO public.hosted_logs "
            "(user_id, signal_id, order_id, action, symbol, target_price, qty, reason, status) "
            "VALUES (:uid, :sid, :oid, :act, :sym, :tp, :qty, :reason, :st)"
        ),
        {
            "uid": user_id, "sid": sid_uuid, "oid": order_id,
            "act": action, "sym": symbol, "tp": target_price,
            "qty": qty, "reason": reason_escaped, "st": status,
        },
    )
    await db.commit()


async def _calc_daily_loss_pct(db: AsyncSession, user_id: int) -> Optional[float]:
    """计算今日浮动亏损百分比"""
    try:
        result = await db.execute(
            _text(
                "SELECT COALESCE(SUM((COALESCE(p.market_price, p.cost_price) - p.cost_price) * p.quantity), 0) as pnl, "
                "a.balance + COALESCE(SUM(p.market_value), 0) as total "
                "FROM public.accounts a "
                "LEFT JOIN public.positions p ON p.account_id = a.id "
                "WHERE a.user_id = :uid GROUP BY a.id"
            ),
            {"uid": user_id},
        )
        row = result.fetchone()
        if row and row[1] and row[1] > 0:
            return round(float(row[0]) / float(row[1]) * 100, 2)
    except Exception as e:
        logger.warning(f"日亏损计算失败: {e}")
    return None


# ─────────────────────────────────────────────────────────
# 核心 API
# ─────────────────────────────────────────────────────────
async def get_hosted_status(db: AsyncSession, user: User) -> HostedStatusResponse:
    """获取当前托管状态"""
    cs = compliance_settings
    uid = user.id
    
    settings = await _get_hosted_settings(db, uid)
    mode = HostedMode(settings["mode"]) if settings else HostedMode.MANUAL
    is_active = mode == HostedMode.AI_HOSTED and (settings is None or settings["enabled_at"] is not None)
    
    today = date.today()
    r = await db.execute(
        _text(
            "SELECT COUNT(*) FROM public.hosted_logs "
            "WHERE user_id = :uid AND DATE(created_at) = :today"
        ),
        {"uid": uid, "today": today},
    )
    active_signals_today = r.scalar() or 0
    
    r2 = await db.execute(
        _text("SELECT COUNT(*) FROM public.hosted_logs WHERE user_id = :uid"),
        {"uid": uid},
    )
    total_trades = r2.scalar() or 0

    # 细分统计
    stats_r = await db.execute(
        _text(
            "SELECT status, COUNT(*) FROM public.hosted_logs WHERE user_id = :uid GROUP BY status"
        ),
        {"uid": uid},
    )
    stat_rows = stats_r.fetchall()
    stat_map = {row[0]: row[1] for row in stat_rows}
    total_triggered = stat_map.get("TRIGGERED", 0)
    total_blocked = stat_map.get("BLOCKED", 0)
    total_skipped = stat_map.get("SKIPPED", 0)
    total_error = stat_map.get("ERROR", 0)
    
    daily_loss_pct = await _calc_daily_loss_pct(db, uid)
    disclaimer = cs.disclaimer_text if cs.disclaimer_enabled else None
    
    return HostedStatusResponse(
        mode=mode,
        enabled_at=settings["enabled_at"] if settings else None,
        disabled_at=settings["disabled_at"] if settings else None,
        is_active=is_active,
        max_position_ratio=settings["max_position_ratio"] if settings else None,
        max_single_trade_ratio=settings["max_single_trade_ratio"] if settings else None,
        min_confidence=settings["min_confidence"] if settings else None,
        total_trades=total_trades,
        total_triggered=total_triggered,
        total_blocked=total_blocked,
        total_skipped=total_skipped,
        total_error=total_error,
        active_signals_today=active_signals_today,
        daily_loss_pct=daily_loss_pct,
        is_audit_mode=cs.is_audit_mode,
        disclaimer=disclaimer,
    )


async def switch_hosted_mode(
    db: AsyncSession,
    user: User,
    mode: HostedMode,
    config: Optional[HostedConfigRequest] = None,
) -> HostedStatusResponse:
    """切换托管模式"""
    cs = compliance_settings
    uid = user.id
    
    if mode == HostedMode.AI_HOSTED:
        if cs.is_audit_mode:
            audit_log(AUDIT_COMPLIANCE_FLAG,
                details={"action": "开启AI托管", "user": user.username, "reason": "IS_AUDIT_MODE=True"},
                risk_level="HIGH")
        if not cs.ai_hosted_enabled:
            raise AppException("AI托管功能暂未开放", status_code=403)
        # 审核模式仍然记录，但不实际执行
        logger.info(f"[审核模式] 用户 {user.username} 开启AI托管（仅记录）")
    
    await _upsert_hosted_settings(db, uid, mode, config)
    
    action = "开启AI托管" if mode == HostedMode.AI_HOSTED else "关闭AI托管"
    audit_log(AUDIT_COMPLIANCE_FLAG,
        details={"action": action, "user": user.username, "mode": mode.value},
        risk_level="MEDIUM")
    
    return await get_hosted_status(db, user)


# ─────────────────────────────────────────────────────────
# 信号 → 订单执行
# ─────────────────────────────────────────────────────────
async def trigger_signal_order(
    db: AsyncSession,
    user: User,
    symbol: str,
    signal_id: str,
    action: str,
    confidence: int,
    target_price: float,
    reasoning: Optional[str] = None,
    quantity: Optional[int] = None,
) -> dict:
    """
    将 AI 信号转换为纸面订单
    
    完整流程：
    1. 检查托管是否开启
    2. 置信度阈值检查
    3. 仓位风控检查（单票上限）
    4. 余额检查
    5. 创建 Order + 更新持仓/余额
    6. 记录日志
    """
    cs = compliance_settings
    uid = user.id
    
    # 1. 托管状态检查
    settings = await _get_hosted_settings(db, uid)
    if not settings or settings["mode"] != "AI_HOSTED":
        await _log_hosted(db, uid, signal_id, None, action, symbol,
                          target_price, None, "SKIPPED", "托管未开启")
        raise AppException("AI托管未开启，请先开启托管模式", status_code=400)
    
    # 2. 置信度阈值
    effective_min = (
        settings["min_confidence"]
        if settings["min_confidence"] is not None
        else cs.min_confidence_for_action
    )
    if confidence < effective_min:
        await _log_hosted(db, uid, signal_id, None, action, symbol,
                          target_price, None, "SKIPPED",
                          f"置信度 {confidence} < 阈值 {effective_min}")
        raise AppException(f"信号置信度 {confidence} < 阈值 {effective_min}，已跳过", status_code=400)
    
    # 3. 获取账户
    result = await db.execute(select(Account).where(Account.user_id == uid))
    account = result.scalar_one_or_none()
    if not account:
        raise AppException("账户不存在", status_code=404)
    
    is_sell = action.upper() == "SELL"

    if is_sell:
        # 卖出：检查持仓 + 使用传入数量
        from sqlalchemy import and_
        pos_check = await db.execute(
            select(Position).where(
                and_(Position.account_id == account.id, Position.symbol == symbol)
            )
        )
        existing = pos_check.scalar_one_or_none()
        if not existing or existing.available <= 0:
            await _log_hosted(db, uid, signal_id, None, action, symbol,
                              target_price, None, "BLOCKED", "无持仓可卖")
            raise AppException("无持仓可卖", status_code=400)

        qty = min(quantity or existing.available, existing.available)
        if qty < LOT_SIZE:
            await _log_hosted(db, uid, signal_id, None, action, symbol,
                              target_price, None, "BLOCKED",
                              f"最小卖出 {LOT_SIZE} 股，当前可用 {existing.available} 股")
            raise AppException(f"可卖数量不足最小单位 {LOT_SIZE} 股", status_code=400)
    else:
        # 买入：风控 + 计算数量
        pos_ok, pos_reason = await _check_position_limit(db, account, target_price, settings)
        if not pos_ok:
            await _log_hosted(db, uid, signal_id, None, action, symbol,
                              target_price, None, "BLOCKED", pos_reason)
            raise AppException(f"风控拦截: {pos_reason}", status_code=403)

        max_trade_ratio = (
            settings["max_single_trade_ratio"]
            if settings["max_single_trade_ratio"] is not None
            else cs.max_single_trade_ratio
        )
        total_assets = float(account.balance)
        pos_result = await db.execute(
            _text("SELECT COALESCE(SUM(market_value), 0) FROM public.positions WHERE account_id = :aid"),
            {"aid": account.id},
        )
        pos_value = float(pos_result.scalar() or 0)
        total_assets += pos_value

        max_amount = total_assets * max_trade_ratio
        qty = quantity if quantity else (int(max_amount / target_price / LOT_SIZE)) * LOT_SIZE

        if qty < LOT_SIZE:
            await _log_hosted(db, uid, signal_id, None, action, symbol,
                              target_price, None, "BLOCKED",
                              f"余额不足，最小需买入 {LOT_SIZE} 股")
            raise AppException(f"可用资金不足最小买入量 {LOT_SIZE} 股", status_code=400)

    # 审核模式
    if cs.is_audit_mode:
        action_cn = "卖出" if is_sell else "买入"
        await _log_hosted(db, uid, signal_id, None, action, symbol,
                          target_price, qty, "BLOCKED",
                          f"审核模式(IS_AUDIT_MODE=True)，模拟{action_cn} {qty} 股")
        raise AppException("审核模式：信号已记录，暂不实际执行交易", status_code=403)
    
    # 7. 实际执行纸面撮合
    try:
        order = await _execute_paper_order(db, account, symbol, action.upper(), target_price, qty, signal_id)
        await _log_hosted(db, uid, signal_id, order.id, action, symbol,
                          target_price, qty, "TRIGGERED",
                          reasoning or f"置信度 {confidence}，AI自动执行")
        
        return {
            "success": True,
            "order_id": order.id,
            "symbol": symbol,
            "name": order.name,
            "qty": qty,
            "price": target_price,
            "amount": float(order.amount),
            "commission": float(order.commission),
            "status": order.status,
            "signal_id": signal_id,
        }
    except Exception as e:
        await _log_hosted(db, uid, signal_id, None, action, symbol,
                          target_price, qty, "ERROR", str(e)[:200])
        raise AppException(f"下单失败: {e}", status_code=500)


async def _check_position_limit(
    db: AsyncSession,
    account: Account,
    target_price: float,
    settings: dict,
) -> Tuple[bool, str]:
    """仓位风控：单票不能超过总资产上限"""
    cs = compliance_settings
    
    # 总资产 = 余额 + 持仓市值
    pos_result = await db.execute(
        _text("SELECT COALESCE(SUM(market_value), 0) FROM public.positions WHERE account_id = :aid"),
        {"aid": account.id},
    )
    pos_value = float(pos_result.scalar() or 0)
    total = float(account.balance) + pos_value
    
    max_ratio = (
        settings["max_position_ratio"]
        if settings["max_position_ratio"] is not None
        else cs.max_position_ratio
    )
    
    # 检查目标股票现有持仓
    existing_pos = await db.execute(
        _text("SELECT COALESCE(SUM(market_value), 0) FROM public.positions WHERE account_id = :aid"),
        {"aid": account.id},
    )
    existing_value = float(existing_pos.scalar() or 0)
    new_total_pos_value = existing_value + target_price * LOT_SIZE
    new_ratio = new_total_pos_value / total if total > 0 else 0
    
    if new_ratio > max_ratio:
        return False, f"单票仓位 {new_ratio:.1%} 将超过上限 {max_ratio:.1%}（总资产 {total:.2f}）"
    
    return True, "OK"


async def _execute_paper_order(
    db: AsyncSession,
    account: Account,
    symbol: str,
    side: str,
    price: float,
    quantity: int,
    signal_id: str,
) -> Order:
    """纸面撮合：创建订单 + 更新持仓/余额"""
    # 成交金额
    amount = price * quantity
    commission = max(amount * COMMISSION_RATE, COMMISSION_MIN)
    tax = 0.0
    if side == "SELL":
        tax = amount * STAMP_TAX_SELL_RATE
        commission += tax
    
    net_amount = amount + commission if side == "BUY" else amount - commission
    
    # 余额检查
    if side == "BUY" and float(account.balance) < net_amount:
        raise AppException(f"余额不足：需要 {net_amount:.2f}，可用 {float(account.balance):.2f}", status_code=400)
    
    # 获取股票名称（简化：留空）
    name = symbol  # 后续可从行情服务获取
    
    # 创建订单
    order = Order(
        user_id=account.user_id,
        account_id=account.id,
        symbol=symbol,
        name=name,
        side=side.lower(),
        order_type="market",
        price=Decimal(str(price)),
        quantity=quantity,
        filled_quantity=quantity,
        filled_price=Decimal(str(price)),
        amount=Decimal(str(amount)),
        commission=Decimal(str(commission)),
        tax=Decimal(str(tax)),
        status="filled",
        signal_id=signal_id,
    )
    db.add(order)
    
    # 更新余额
    if side == "BUY":
        account.balance = Decimal(str(float(account.balance) - net_amount))
    else:
        account.balance = Decimal(str(float(account.balance) + net_amount))
    
    # 更新持仓
    await _sync_position(db, account.id, account.user_id, symbol, side, price, quantity)
    await db.commit()
    await db.refresh(order)
    return order


async def _sync_position(
    db: AsyncSession,
    account_id: int,
    user_id: int,
    symbol: str,
    side: str,
    price: float,
    quantity: int,
):
    """同步持仓"""
    result = await db.execute(
        select(Position).where(
            and_(Position.account_id == account_id, Position.symbol == symbol)
        )
    )
    pos = result.scalar_one_or_none()
    
    if side == "BUY":
        if pos:
            new_qty = pos.quantity + quantity
            new_avg = (float(pos.cost_price) * float(pos.quantity) + price * quantity) / new_qty
            pos.quantity = new_qty
            pos.available = new_qty
            pos.cost_price = Decimal(str(round(new_avg, 4)))
            pos.cost_amount = Decimal(str(round(new_avg * new_qty, 2)))
            pos.market_price = Decimal(str(price))
            pos.market_value = Decimal(str(new_qty * price))
        else:
            pos = Position(
                user_id=user_id,
                account_id=account_id,
                symbol=symbol,
                quantity=quantity,
                available=quantity,
                cost_price=Decimal(str(price)),
                cost_amount=Decimal(str(price * quantity)),
                market_price=Decimal(str(price)),
                market_value=Decimal(str(quantity * price)),
            )
            db.add(pos)
    else:  # SELL
        if pos:
            new_qty = pos.quantity - quantity
            if new_qty <= 0:
                await db.delete(pos)
            else:
                pos.quantity = new_qty
                pos.available = new_qty
                pos.market_price = Decimal(str(price))
                pos.market_value = Decimal(str(new_qty * price))
                pos.cost_amount = Decimal(str(float(pos.cost_price) * new_qty))


# ─────────────────────────────────────────────────────────
# 日志查询
# ─────────────────────────────────────────────────────────
async def get_hosted_logs(
    db: AsyncSession,
    user: User,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[int, list]:
    """获取托管执行日志"""
    uid = user.id
    r = await db.execute(
        _text("SELECT COUNT(*) FROM public.hosted_logs WHERE user_id = :uid"),
        {"uid": uid},
    )
    total = r.scalar() or 0
    
    rows_r = await db.execute(
        _text(
            "SELECT id, signal_id, order_id, action, symbol, target_price, qty, "
            "reason, status, created_at "
            "FROM public.hosted_logs WHERE user_id = :uid "
            "ORDER BY created_at DESC LIMIT :lim"
        ),
        {"uid": uid, "lim": limit},
    )
    rows = rows_r.fetchall()
    
    # 提取所有股票代码，获取股票名称
    symbols = list({r[4] for r in rows if r[4]})
    symbol_names: dict[str, str] = {}
    if symbols:
        from app.integrations.market_data import get_market_data_adapter
        adapter = get_market_data_adapter()
        for sym in symbols:
            try:
                q: Any = await adapter.get_quote(sym)  # type: ignore
                symbol_names[sym] = q.name
            except Exception:
                symbol_names[sym] = sym  # 回退为代码

    logs = [
        HostedLogItem(
            id=str(r[0]),
            signal_id=str(r[1]) if r[1] else None,
            order_id=r[2] if r[2] else None,
            action=r[3],
            symbol=r[4],
            symbol_name=symbol_names.get(r[4]),
            target_price=float(r[5]) if r[5] is not None else None,
            qty=r[6],
            reason=r[7],
            status=r[8],
            created_at=r[9],
        )
        for r in rows
    ]
    return total, logs
