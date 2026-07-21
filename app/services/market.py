"""
app.services.market — 行情数据服务（v2：使用 adapter 架构）

改造点（v1 → v2）：
1. 不再直接 import akshare，改为通过 app.integrations.market_data 获取 adapter
2. 保持原有接口（fetch_realtime_quotes / fetch_kline）向后兼容
3. QuoteData / KLineData → 转换为 API schema (QuoteItem / KLineItem)

数据源选择：
- 默认自动降级：akshare → sina → mock
- 通过环境变量 MARKET_DATA_SOURCE=sina/akshare/mock 显式指定
- 服务器目前无法用 akshare（Python 3.12 兼容性问题），所以默认会走到 sina
"""
import logging
from typing import List

from app.core.exceptions import AppException
from app.schemas.market import QuoteItem, KLineItem
from app.integrations.market_data import get_market_data_adapter
from app.integrations.market_data.base import (
    QuoteData as AdapterQuoteData,
    KLineData as AdapterKLineData,
)

logger = logging.getLogger(__name__)


def _quote_to_item(q: AdapterQuoteData) -> QuoteItem:
    """Adapter 数据模型 → API 响应模型"""
    return QuoteItem(
        symbol=q.symbol,
        name=q.name,
        price=q.price,
        open=q.open,
        high=q.high,
        low=q.low,
        close=q.prev_close,  # 字段名差异：prev_close → close
        change=q.change,
        change_pct=q.change_pct,
        volume=q.volume,
        amount=q.amount,
        turnover_rate=q.turnover_rate,
        pe_ratio=q.pe_ratio,
        market_cap=q.market_cap,
    )


def _kline_to_item(k: AdapterKLineData) -> KLineItem:
    """Adapter 数据模型 → API 响应模型"""
    return KLineItem(
        date=k.date,
        open=k.open,
        close=k.close,
        high=k.high,
        low=k.low,
        volume=k.volume,
        amount=k.amount or 0.0,
        amplitude=k.amplitude,
        change_pct=k.change_pct,
        change=k.change,
        turnover_rate=k.turnover_rate,
    )


async def fetch_realtime_quotes(symbols: List[str]) -> List[QuoteItem]:
    """
    获取实时行情报价（向后兼容方法）

    通过 adapter 抽象获取数据，业务层不再关心具体数据源。

    Args:
        symbols: 股票代码列表，如 ["600519.SH", "000001.SZ"]

    Returns:
        QuoteItem 列表
    """
    adapter = get_market_data_adapter()
    logger.debug(f"使用 {adapter.name} adapter 获取 {len(symbols)} 只股票行情")

    quotes = await adapter.get_quotes(symbols)
    return [_quote_to_item(q) for q in quotes]



async def fetch_stock_detail(symbol: str) -> dict:
    """
    获取股票详情（行情 + K 线 + 技术指标），用于行情详情页。

    合并一次行情调用 + 两次 K 线调用（日/周），计算常用均线。

    Args:
        symbol: 股票代码，如 "600519.SH"

    Returns:
        字典，包含行情、K 线数据、均线等技术指标
    """
    from app.schemas.market import StockDetail

    # 1. 行情
    quotes = await fetch_realtime_quotes([symbol])
    if not quotes:
        raise AppException(code="SYMBOL_NOT_FOUND", message=f"未找到 {symbol} 的行情", status_code=404)
    q = quotes[0]

    # 2. K 线（日线 120 条给均线计算，周线 60 条）
    klines_daily = await fetch_kline(symbol, period="daily", count=120)
    klines_weekly = await fetch_kline(symbol, period="weekly", count=60)

    # 3. 计算均线
    ma5 = _compute_ma(klines_daily, 5)
    ma10 = _compute_ma(klines_daily, 10)
    ma20 = _compute_ma(klines_daily, 20)
    ma60 = _compute_ma(klines_daily, 60)

    # 4. 计算技术指标
    rsi_6 = _compute_rsi(klines_daily, 6)
    rsi_14 = _compute_rsi(klines_daily, 14)
    macd_value, macd_signal, macd_hist = _compute_macd(klines_daily, 12, 26, 9)
    boll_upper, boll_mid, boll_lower = _compute_bollinger(klines_daily, 20, 2.0)

    price = q.price
    return {
        "symbol": q.symbol,
        "name": q.name,
        "market": "A" if q.symbol.endswith((".SH", ".SZ")) else "HK",
        "price": price,
        "open": q.open,
        "high": q.high,
        "low": q.low,
        "prev_close": q.close,
        "change": q.change,
        "change_pct": q.change_pct,
        "volume": q.volume,
        "amount": q.amount,
        "turnover_rate": q.turnover_rate,
        "pe_ratio": q.pe_ratio,
        "pb_ratio": q.pb_ratio,
        "market_cap": q.market_cap,
        "circul_cap": q.circul_cap,
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "ma60": ma60,
        "ma5_pct": round((price - ma5) / ma5 * 100, 2) if ma5 and ma5 > 0 else None,
        "ma20_pct": round((price - ma20) / ma20 * 100, 2) if ma20 and ma20 > 0 else None,
        "rsi_6": rsi_6,
        "rsi_14": rsi_14,
        "macd_value": macd_value,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist,
        "boll_upper": boll_upper,
        "boll_mid": boll_mid,
        "boll_lower": boll_lower,
        "klines_daily": klines_daily[-60:],  # 只返回最近 60 日
        "klines_weekly": klines_weekly,
    }


def _compute_ma(klines: list, period: int) -> float | None:
    """计算 N 日均线（简单移动平均）"""
    if len(klines) < period:
        return None
    closes = [k.close for k in klines[-period:]]
    return round(sum(closes) / period, 2)


def _get_closes(klines: list) -> list[float]:
    """提取收盘价数组"""
    return [k.close for k in klines]


def _compute_rsi(klines: list, period: int = 14) -> float | None:
    """
    计算 RSI（相对强弱指标）。

    RSI = 100 - 100 / (1 + RS)
    RS = 平均涨幅 / 平均跌幅（指数移动平均）
    """
    closes = _get_closes(klines)
    if len(closes) < period + 1:
        return None

    # 计算每日涨跌
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # 初始 SMA
    gains = [max(d, 0) for d in deltas[:period]]
    losses = [max(-d, 0) for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0

    # 后续 EMA
    alpha = 1.0 / period
    for d in deltas[period:]:
        gain = max(d, 0)
        loss = max(-d, 0)
        avg_gain = avg_gain * (1 - alpha) + gain * alpha
        avg_loss = avg_loss * (1 - alpha) + loss * alpha

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - 100.0 / (1.0 + rs)
    return round(rsi, 2)


def _compute_macd(
    klines: list, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float | None, float | None, float | None]:
    """
    计算 MACD（指数平滑移动平均线）。

    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(MACD, signal)
    Histogram = MACD - Signal
    """
    closes = _get_closes(klines)
    if len(closes) < slow + signal:
        return None, None, None

    def _ema(data: list[float], period: int) -> list[float]:
        """指数移动平均"""
        multiplier = 2.0 / (period + 1)
        ema = [sum(data[:period]) / period]  # 初始 SMA
        for i in range(period, len(data)):
            ema.append((data[i] - ema[-1]) * multiplier + ema[-1])
        return ema

    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)

    # MACD 线 = EMA_fast - EMA_slow
    offset = slow - fast
    macd_line = [
        ema_fast[i + offset] - ema_slow[i]
        for i in range(len(ema_slow))
    ]

    # Signal 线 = EMA(MACD, signal)
    signal_line = _ema(macd_line, signal)

    # 取最新值
    macd_val = round(macd_line[-1], 3)
    sig_val = round(signal_line[-1], 3)
    hist_val = round(macd_val - sig_val, 3)

    return macd_val, sig_val, hist_val


def _compute_bollinger(
    klines: list, period: int = 20, num_std: float = 2.0
) -> tuple[float | None, float | None, float | None]:
    """
    计算布林带。

    中轨 = MA(period)
    上轨 = 中轨 + num_std * 标准差
    下轨 = 中轨 - num_std * 标准差
    """
    closes = _get_closes(klines)
    if len(closes) < period:
        return None, None, None

    recent = closes[-period:]
    ma = sum(recent) / period
    variance = sum((c - ma) ** 2 for c in recent) / period
    std = variance ** 0.5

    upper = round(ma + num_std * std, 2)
    mid = round(ma, 2)
    lower = round(ma - num_std * std, 2)

    return upper, mid, lower


async def fetch_kline(
    symbol: str,
    period: str = "daily",
    count: int = 100,
) -> List[KLineItem]:
    """
    获取 K 线历史数据（向后兼容方法）

    Args:
        symbol: 股票代码，如 "600519.SH"
        period: 周期，"daily"/"weekly"/"monthly"
        count: 返回条数

    Returns:
        KLineItem 列表（按日期升序）
    """
    from app.integrations.market_data.base import Period

    period_map = {
        "daily": Period.DAILY,
        "weekly": Period.WEEKLY,
        "monthly": Period.MONTHLY,
    }
    ak_period = period_map.get(period, Period.DAILY)

    adapter = get_market_data_adapter()
    logger.debug(f"使用 {adapter.name} adapter 获取 {symbol} K线 ({period}, {count}条)")

    klines = await adapter.get_kline(symbol, ak_period, count)
    items = [_kline_to_item(k) for k in klines]
    items.reverse()  # Sina 返回最新在前，转为最早在前
    return items


# ============== 排行榜（新增） ==============
async def fetch_ranking(
    rank_type: str = "gainers",
    limit: int = 20,
) -> list:
    """
    获取全市场 A 股排名（涨幅榜/跌幅榜/热门榜）。

    数据源：东方财富公开 HTTP API（无需依赖 akshare）。

    Args:
        rank_type: "gainers"（涨幅榜）/ "losers"（跌幅榜）/ "hot"（热门，按成交额）
        limit: 返回条数（≤50）

    Returns:
        RankItem 列表
    """
    from app.integrations.market_data.tencent import fetch_ranking as em_fetch_ranking

    if rank_type == "gainers":
        sort_by, order = "change_pct", "desc"
    elif rank_type == "losers":
        sort_by, order = "change_pct", "asc"
    elif rank_type == "hot":
        sort_by, order = "amount", "desc"
    else:
        rank_type = "gainers"
        sort_by, order = "change_pct", "desc"

    limit = min(limit, 50)

    try:
        items = await em_fetch_ranking(sort_by=sort_by, order=order, limit=limit)
    except Exception as e:
        logger.error(f"获取排行榜失败: {e}")
        return []

    # 转换为 schema
    from app.schemas.market import RankItem as RankSchema
    return [
        RankSchema(
            symbol=item.symbol,
            code=item.code,
            name=item.name,
            price=item.price,
            change=item.change,
            change_pct=item.change_pct,
            volume=item.volume,
            amount=item.amount,
            turnover_rate=item.turnover_rate,
            high=item.high,
            low=item.low,
            open=item.open,
            prev_close=item.prev_close,
            pe_ratio=item.pe_ratio,
            market_cap=item.market_cap,
            circul_cap=item.circul_cap,
        )
        for item in items
    ]
