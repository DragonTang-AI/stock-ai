"""
app.integrations.market_data.akshare — AkShare 库适配器

AkShare 是基于 Python 的开源财经数据接口库，数据源丰富。

注意：
1. AkShare 在 Python 3.12 上有兼容性问题（py_mini_racer 依赖 pkgutil.ImpImporter）
2. 如果环境无法安装 AkShare，应该降级到其他 adapter
3. factory.py 会自动检测可用性并选择合适的 adapter

字段映射参考（AkShare stock_zh_a_spot_em）：
  代码, 名称, 最新价, 涨跌幅, 涨跌额, 成交量, 成交额, 振幅, 最高, 最低, 今开, 昨收,
  换手率, 市盈率-动态, 市净率, 总市值, 流通市值, 涨速, 5分钟涨跌, 60日涨跌幅, 年初至今涨跌幅
"""
import logging
import asyncio
from typing import List, Optional

from app.integrations.market_data.base import (
    MarketDataAdapter,
    QuoteData,
    KLineData,
    Period,
    DataSourceError,
)

logger = logging.getLogger(__name__)

# AkShare 周期映射
AKSHARE_PERIOD_MAP = {
    Period.DAILY: "daily",
    Period.WEEKLY: "weekly",
    Period.MONTHLY: "monthly",
}


def _normalize_symbol(symbol: str) -> str:
    """
    标准代码转 AkShare 格式（去掉后缀）
    """
    if "." in symbol:
        return symbol.split(".")[0]
    return symbol


def _get_market_suffix(code: str) -> str:
    """根据代码判断市场后缀"""
    if code.startswith("6"):
        return f"{code}.SH"
    elif code.startswith(("0", "3")):
        return f"{code}.SZ"
    elif code.startswith(("4", "8")):
        return f"{code}.BJ"
    return f"{code}.UNKNOWN"


def is_akshare_available() -> bool:
    """检查 AkShare 是否可用（导入测试）"""
    try:
        import akshare as ak  # noqa: F401

        return True
    except (ImportError, Exception) as e:
        logger.debug(f"AkShare 不可用: {e}")
        return False


class AkshareAdapter(MarketDataAdapter):
    """
    AkShare 数据源适配器

    优点：
    - 数据源丰富（A股/港股/美股/期货/基金/指数）
    - 字段完整（市净率/总市值/流通市值都有）
    - 持续维护

    缺点：
    - 依赖重（pandas + lxml + py_mini_racer + 各种 JS runtime）
    - Python 3.12 兼容性问题
    - 速度慢（同步阻塞，需要 run_in_executor）
    """

    name = "akshare"

    def __init__(self):
        self._ak = None
        self._initialized = False

    def _ensure_akshare(self):
        """延迟导入 AkShare"""
        if not self._initialized:
            try:
                import akshare as ak

                self._ak = ak
                self._initialized = True
            except Exception as e:
                raise DataSourceError(
                    self.name,
                    f"AkShare 初始化失败: {type(e).__name__}: {e}",
                    original=e,
                )
        return self._ak

    async def get_quote(self, symbol: str) -> QuoteData:
        results = await self.get_quotes([symbol])
        if not results:
            from app.integrations.market_data.base import SymbolNotFoundError

            raise SymbolNotFoundError(self.name, symbol)
        return results[0]

    async def get_quotes(self, symbols: List[str]) -> List[QuoteData]:
        """批量获取实时行情"""
        if not symbols:
            return []

        ak = self._ensure_akshare()
        loop = asyncio.get_event_loop()

        def _fetch():
            try:
                df = ak.stock_zh_a_spot_em()
            except Exception as e:
                raise DataSourceError(
                    self.name,
                    f"获取实时行情失败: {type(e).__name__}: {e}",
                    original=e,
                )

            results = []
            for symbol in symbols:
                code = _normalize_symbol(symbol)
                row = df[df["代码"] == code]
                if row.empty:
                    continue
                row = row.iloc[0]

                quote = QuoteData(
                    symbol=_get_market_suffix(code),
                    name=str(row["名称"]),
                    price=float(row["最新价"]),
                    open=float(row["今开"]),
                    high=float(row["最高"]),
                    low=float(row["最低"]),
                    prev_close=float(row["昨收"]),
                    change=float(row["涨跌额"]),
                    change_pct=float(row["涨跌幅"]),
                    volume=int(row["成交量"]),
                    amount=float(row["成交额"]),
                    turnover_rate=float(row["换手率"]) if "换手率" in row else None,
                    pe_ratio=float(row["市盈率-动态"]) if "市盈率-动态" in row else None,
                    pb_ratio=float(row["市净率"]) if "市净率" in row else None,
                    market_cap=float(row["总市值"]) if "总市值" in row else None,
                    circul_cap=float(row["流通市值"]) if "流通市值" in row else None,
                )
                results.append(quote)
            return results

        return await loop.run_in_executor(None, _fetch)

    async def get_kline(
        self,
        symbol: str,
        period: Period = Period.DAILY,
        count: int = 100,
    ) -> List[KLineData]:
        """获取 K 线历史数据"""
        ak = self._ensure_akshare()
        loop = asyncio.get_event_loop()

        def _fetch():
            code = _normalize_symbol(symbol)
            ak_period = AKSHARE_PERIOD_MAP.get(period, "daily")

            try:
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period=ak_period,
                    start_date="20200101",
                    end_date="20291231",
                    adjust="",
                )
            except Exception as e:
                raise DataSourceError(
                    self.name,
                    f"获取K线失败: {type(e).__name__}: {e}",
                    original=e,
                )

            df = df.tail(count)

            results = []
            for _, row in df.iterrows():
                kline = KLineData(
                    symbol=_get_market_suffix(code),
                    date=str(row["日期"]),
                    period=period,
                    open=float(row["开盘"]),
                    close=float(row["收盘"]),
                    high=float(row["最高"]),
                    low=float(row["最低"]),
                    volume=int(row["成交量"]),
                    amount=float(row["成交额"]) if "成交额" in row else None,
                    change_pct=float(row["涨跌幅"]) if "涨跌幅" in row else None,
                    change=float(row["涨跌额"]) if "涨跌额" in row else None,
                    turnover_rate=float(row["换手率"]) if "换手率" in row else None,
                )
                results.append(kline)
            return results

        return await loop.run_in_executor(None, _fetch)
