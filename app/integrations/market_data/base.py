"""
app.integrations.market_data.base — 行情数据源抽象基类

设计目标：
1. 稳定的接口：业务层只依赖这个文件，不直接 import 实现
2. 异步优先：所有方法都是 async，便于并发和事件循环
3. 类型严格：用 dataclass 替代 dict，减少字段拼写错误
4. 易测试：方法签名清晰，可以轻松 mock
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class Period(str, Enum):
    """K 线周期"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class QuoteData:
    """
    实时行情数据

    字段命名参考国内通用规范（参考通达信/同花顺的字段名），
    便于从不同数据源适配。
    """

    symbol: str  # 完整代码，如 "600519.SH"
    name: str  # 股票名称
    price: float  # 当前价
    open: float  # 今开
    high: float  # 最高
    low: float  # 最低
    prev_close: float  # 昨收
    change: float  # 涨跌额 = price - prev_close
    change_pct: float  # 涨跌幅（%）
    volume: int  # 成交量（手）
    amount: float  # 成交额（元）

    # 可选字段（不同数据源支持度不同）
    turnover_rate: Optional[float] = None  # 换手率（%）
    pe_ratio: Optional[float] = None  # 市盈率（动/静）
    pb_ratio: Optional[float] = None  # 市净率
    market_cap: Optional[float] = None  # 总市值（亿元）
    circul_cap: Optional[float] = None  # 流通市值（亿元）
    timestamp: Optional[datetime] = None  # 数据时间戳

    @classmethod
    def from_sina(
        cls,
        symbol: str,
        name: str,
        fields: List[str],
    ) -> "QuoteData":
        """
        从新浪 API 返回的字段数组构造 QuoteData

        新浪字段顺序（按 var hq_str_shXXXXXXX="..." 拆分）：
        [0] name        股票名字
        [1] open        今日开盘价
        [2] prev_close  昨日收盘价
        [3] price       当前价格
        [4] high        今日最高价
        [5] low         今日最低价
        [6] bid1        竞买价（买一）
        [7] ask1        竞卖价（卖一）
        [8] volume      成交量（手，1手=100股）
        [9] amount      成交金额（元）
        [10] bid1_vol   买一申请量
        ... 买卖盘（5 档）
        [30] date       日期 YYYY-MM-DD
        [31] time       时间 HH:MM:SS
        [32] status     状态码（00=正常）
        [33] change_pct 涨跌幅（%）
        [34] change     涨跌额
        [35] high_52w   52周最高
        [36] low_52w    52周最低

        实际新浪返回 34 字段（无 52 周高/低），下面代码兼容 34 字段。
        """
        if len(fields) < 33:
            raise ValueError(f"新浪字段数不足: {len(fields)}, 期望 >= 33")

        # 新浪的 volume 单位是"手"，1手=100股
        # 为了和 AkShare 一致（AkShare 也是"手"），这里保持"手"
        volume_in_lots = int(fields[8])  # 手
        amount_yuan = float(fields[9])  # 元

        prev_close = float(fields[2])
        price = float(fields[3])
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        # 时间戳解析：[30]=日期, [31]=时间
        timestamp = None
        if len(fields) > 31 and fields[30] and fields[31]:
            try:
                timestamp = datetime.strptime(
                    f"{fields[30]} {fields[31]}", "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                pass

        return cls(
            symbol=symbol,
            name=name,
            price=price,
            open=float(fields[1]),
            high=float(fields[4]),
            low=float(fields[5]),
            prev_close=prev_close,
            change=change,
            change_pct=change_pct,
            volume=volume_in_lots,
            amount=amount_yuan,
            timestamp=timestamp,
        )


@dataclass
class KLineData:
    """K 线数据"""

    symbol: str  # 完整代码，如 "600519.SH"
    date: str  # 日期，如 "2024-01-01"
    period: Period  # 周期
    open: float
    close: float
    high: float
    low: float
    volume: int  # 成交量（手）
    amount: Optional[float] = None  # 成交额（元）
    change_pct: Optional[float] = None  # 涨跌幅（%）
    change: Optional[float] = None  # 涨跌额
    turnover_rate: Optional[float] = None  # 换手率（%）
    amplitude: Optional[float] = None  # 振幅（%）


class MarketDataAdapter(ABC):
    """
    行情数据源抽象基类

    所有数据源实现必须继承这个类并实现所有抽象方法。
    业务层应该只通过 Protocol/ABC 引用，不要直接 import 具体实现。
    """

    name: str = "abstract"  # 数据源标识，用于日志

    @abstractmethod
    async def get_quote(self, symbol: str) -> QuoteData:
        """
        获取单只股票的实时行情

        Args:
            symbol: 标准股票代码，如 "600519.SH" / "000001.SZ"

        Returns:
            QuoteData 实例

        Raises:
            SymbolNotFoundError: 股票代码不存在
            DataSourceError: 数据源错误（网络/解析等）
        """
        raise NotImplementedError

    @abstractmethod
    async def get_quotes(self, symbols: List[str]) -> List[QuoteData]:
        """
        批量获取实时行情

        尽量使用数据源支持的批量接口（如新浪的 list=sh600519,sz000001），
        减少请求次数。

        Args:
            symbols: 标准股票代码列表

        Returns:
            QuoteData 列表（顺序可能与输入不同，需要按 symbol 自行匹配）
            如果某只股票查询失败，应该跳过而不是抛异常（保证部分成功）

        Raises:
            DataSourceError: 数据源整体不可用
        """
        raise NotImplementedError

    @abstractmethod
    async def get_kline(
        self,
        symbol: str,
        period: Period = Period.DAILY,
        count: int = 100,
    ) -> List[KLineData]:
        """
        获取 K 线历史数据

        Args:
            symbol: 标准股票代码
            period: K 线周期
            count: 返回条数（最近的 N 条）

        Returns:
            KLineData 列表，按日期升序排列

        Raises:
            SymbolNotFoundError: 股票代码不存在
            DataSourceError: 数据源错误
        """
        raise NotImplementedError

    async def health_check(self) -> bool:
        """
        健康检查（可选实现）

        默认实现：尝试获取贵州茅台（600519.SH）的行情
        子类可以重写以做更精确的检查
        """
        try:
            await self.get_quote("600519.SH")
            return True
        except Exception:
            return False


# 自定义异常
class DataSourceError(Exception):
    """数据源错误基类"""

    def __init__(self, source: str, message: str, original: Optional[Exception] = None):
        self.source = source
        self.message = message
        self.original = original
        super().__init__(f"[{source}] {message}")


class SymbolNotFoundError(DataSourceError):
    """股票代码不存在"""

    def __init__(self, source: str, symbol: str):
        self.symbol = symbol
        super().__init__(source, f"股票代码不存在: {symbol}")
