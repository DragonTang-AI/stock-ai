"""
app/services/market.py — 行情数据服务（AkShare 封装）
"""
import akshare as ak
from typing import List, Optional
from app.schemas.market import QuoteItem, KLineItem
import asyncio
from functools import partial


def _normalize_symbol(symbol: str) -> str:
    """
    将标准股票代码转换为 AkShare 格式。

    AkShare 使用纯数字代码（如 "600519"），不带后缀。
    支持格式：
    - "600519.SH" → "600519"
    - "000001.SZ" → "000001"
    """
    if "." in symbol:
        return symbol.split(".")[0]
    return symbol


def _get_market_suffix(symbol: str) -> str:
    """根据股票代码判断市场后缀（.SH / .SZ）"""
    code = _normalize_symbol(symbol)
    if code.startswith("6"):
        return f"{code}.SH"
    elif code.startswith(("0", "3")):
        return f"{code}.SZ"
    else:
        return symbol  # 未知格式，原样返回


async def fetch_realtime_quotes(symbols: List[str]) -> List[QuoteItem]:
    """
    获取实时行情报价。

    使用 AkShare `stock_zh_a_spot_em()` 获取全市场实时数据，然后过滤指定股票。

    Args:
        symbols: 股票代码列表，如 ["600519.SH", "000001.SZ"]

    Returns:
        QuoteItem 列表
    """
    loop = asyncio.get_event_loop()

    # AkShare 是同步库，用 run_in_executor 避免阻塞
    def _fetch():
        df = ak.stock_zh_a_spot_em()
        # 列名参考 AkShare 文档：
        # 代码, 名称, 最新价, 涨跌幅, 涨跌额, 成交量, 成交额, 振幅, 最高, 最低, 今开, 昨收, 换手率, 市盈率, 总市值
        result = []
        for symbol in symbols:
            code = _normalize_symbol(symbol)
            row = df[df["代码"] == code]
            if row.empty:
                continue
            row = row.iloc[0]
            quote = QuoteItem(
                symbol=_get_market_suffix(code),
                name=row["名称"],
                price=float(row["最新价"]),
                open=float(row["今开"]),
                high=float(row["最高"]),
                low=float(row["最低"]),
                close=float(row["昨收"]),
                change=float(row["涨跌额"]),
                change_pct=float(row["涨跌幅"]),
                volume=int(row["成交量"]),
                amount=float(row["成交额"]),
                turnover_rate=float(row["换手率"]) if "换手率" in row else None,
                pe_ratio=float(row["市盈率"]) if "市盈率" in row else None,
                market_cap=float(row["总市值"]) if "总市值" in row else None,
            )
            result.append(quote)
        return result

    return await loop.run_in_executor(None, _fetch)


async def fetch_kline(
    symbol: str,
    period: str = "daily",
    count: int = 100,
) -> List[KLineItem]:
    """
    获取 K 线历史数据。

    使用 AkShare `stock_zh_a_hist()` 获取历史 K 线。

    Args:
        symbol: 股票代码，如 "600519.SH"
        period: 周期，"daily"/"weekly"/"monthly"
        count: 返回条数

    Returns:
        KLineItem 列表（按日期升序）
    """
    loop = asyncio.get_event_loop()

    def _fetch():
        code = _normalize_symbol(symbol)
        # period 映射：daily→"日线", weekly→"周线", monthly→"月线"
        period_map = {"daily": "日线", "weekly": "周线", "monthly": "月线"}
        ak_period = period_map.get(period, "日线")

        # 获取最近 count 条
        df = ak.stock_zh_a_hist(
            symbol=code,
            period=ak_period,
            start_date="20200101",  # 取足够长的时间范围
            end_date="20291231",
            adjust="",
        )
        # 取最后 count 条
        df = df.tail(count)

        # 列名参考：日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
        result = []
        for _, row in df.iterrows():
            item = KLineItem(
                date=str(row["日期"]),
                open=float(row["开盘"]),
                close=float(row["收盘"]),
                high=float(row["最高"]),
                low=float(row["最低"]),
                volume=int(row["成交量"]),
                amount=float(row["成交额"]) if "成交额" in row else None,
                amplitude=float(row["振幅"]) if "振幅" in row else None,
                change_pct=float(row["涨跌幅"]) if "涨跌幅" in row else None,
                change=float(row["涨跌额"]) if "涨跌额" in row else None,
                turnover_rate=float(row["换手率"]) if "换手率" in row else None,
            )
            result.append(item)
        return result

    return await loop.run_in_executor(None, _fetch)
