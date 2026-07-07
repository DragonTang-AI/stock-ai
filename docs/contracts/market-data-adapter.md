# Market Data Adapter 接口契约

**版本**: v1.0
**日期**: 2026-07-02
**状态**: ✅ 实施完成
**分支**: `feat/phase2-akshare-adapter`

---

## 设计目标

1. **抽象优先**：业务层只依赖 `base.py`，不直接 import 实现
2. **零兼容性问题**：新浪 HTTP API 无外部依赖，绕过 AkShare Python 3.12 兼容性障碍
3. **向后兼容**：保留 AkShare 实现，Python 3.12 兼容性问题解决后可无缝切换
4. **可测试**：Mock adapter 支持无网络测试

---

## 接口定义

### MarketDataAdapter (ABC)

```python
class MarketDataAdapter(ABC):
    name: str  # "sina" | "akshare" | "mock"

    async def get_quote(symbol: str) -> QuoteData:
        """获取单只股票实时行情"""
        ...

    async def get_quotes(symbols: list[str]) -> list[QuoteData]:
        """批量获取实时行情（部分失败不抛异常）"""
        ...

    async def get_kline(
        symbol: str,
        period: Period = Period.DAILY,
        count: int = 100,
    ) -> list[KLineData]:
        """获取 K 线历史数据（按日期升序）"""
        ...

    async def health_check(self) -> bool:
        """健康检查（默认：获取茅台行情）"""
        ...
```

### QuoteData (dataclass)

```python
@dataclass
class QuoteData:
    symbol: str           # "600519.SH"
    name: str             # "贵州茅台"
    price: float          # 当前价
    open: float           # 今开
    high: float           # 最高
    low: float            # 最低
    prev_close: float     # 昨收
    change: float         # 涨跌额
    change_pct: float     # 涨跌幅（%）
    volume: int           # 成交量（手）
    amount: float         # 成交额（元）

    # 可选字段
    turnover_rate: float | None = None   # 换手率（%）
    pe_ratio: float | None = None        # 市盈率
    pb_ratio: float | None = None        # 市净率
    market_cap: float | None = None      # 总市值（亿元）
    circul_cap: float | None = None      # 流通市值（亿元）
    timestamp: datetime | None = None    # 数据时间
```

### KLineData (dataclass)

```python
@dataclass
class KLineData:
    symbol: str           # "600519.SH"
    date: str             # "2024-01-01"
    period: Period        # DAILY / WEEKLY / MONTHLY
    open: float
    close: float
    high: float
    low: float
    volume: int           # 成交量（手）
    amount: float | None  # 成交额（元）
    change_pct: float | None   # 涨跌幅（%）
    change: float | None       # 涨跌额
    turnover_rate: float | None  # 换手率（%）
    amplitude: float | None   # 振幅（%）
```

### Period (Enum)

```python
class Period(str, Enum):
    DAILY = "daily"    # 日线
    WEEKLY = "weekly"  # 周线
    MONTHLY = "monthly"  # 月线
```

---

## 数据源实现

| 实现 | 标识 | 依赖 | 状态 |
|------|------|------|------|
| SinaAdapter | `sina` | httpx | ✅ 默认 |
| AkshareAdapter | `akshare` | akshare + pandas | 🔶 降级 |
| MockAdapter | `mock` | 无 | 🔶 测试用 |

---

## 环境变量

| 变量 | 值 | 说明 |
|------|-----|------|
| `MARKET_DATA_SOURCE` | `sina` / `akshare` / `mock` | 显式指定数据源 |
| （未指定） | - | 自动降级：akshare → sina → mock |

---

## 新浪 API 详情

### 实时行情

```
GET http://hq.sinajs.cn/list=sh600519,sz000001
Headers: Referer: https://finance.sina.com.cn/
```

**响应字段（33个，逗号分隔）：**

| 索引 | 字段 | 示例 |
|------|------|------|
| 0 | name | 贵州茅台 |
| 1 | open | 1193.010 |
| 2 | prev_close | 1193.010 |
| 3 | price | 1203.000 |
| 4 | high | 1215.520 |
| 5 | low | 1190.510 |
| 6 | bid1 | 1203.000 |
| 7 | ask1 | 1204.000 |
| 8 | volume | 5087015（手） |
| 9 | amount | 6122360932.000（元） |
| 10-19 | bid1~bid5 vol | 买单量 |
| 20-29 | ask1~ask5 vol | 卖单量 |
| 30 | date | 2026-07-02 |
| 31 | time | 15:00:03 |
| 32 | status | 00（正常） |

### K 线

```
GET https://quotes.sina.cn/cn/api/jsonp_v2.php/var=callback/CN_MarketDataService.getKLineData
Params: symbol=sh600519, scale=240, ma=no, datalen=100
```

scale 映射：`daily=240`, `weekly=1680`, `monthly=7200`

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| day | string | 日期 YYYY-MM-DD |
| open | string | 开盘价 |
| high | string | 最高价 |
| low | string | 最低价 |
| close | string | 收盘价 |
| volume | string | 成交量（手） |
| amount | string | 成交额（元） |

---

## 使用方式

```python
from app.integrations.market_data import get_market_data_adapter
from app.integrations.market_data.base import Period

adapter = get_market_data_adapter()
quotes = await adapter.get_quotes(["600519.SH", "000001.SZ"])
klines = await adapter.get_kline("600519.SH", Period.DAILY, count=100)
```

---

## 文件结构

```
app/integrations/
├── __init__.py
└── market_data/
    ├── __init__.py        # 导出 public API
    ├── base.py            # 抽象基类 + dataclass + 异常
    ├── sina.py            # 新浪 HTTP API 实现（✅ 默认）
    ├── akshare.py         # AkShare 库实现（🔶 降级）
    └── factory.py         # 工厂方法 + 单例缓存
```

---

## 与 Phase 1 / T-S001 的关系

Phase 1 的 `app/services/market.py` 已改造为使用 adapter：

- `fetch_realtime_quotes()` → 调用 `adapter.get_quotes()`
- `fetch_kline()` → 调用 `adapter.get_kline()`

业务层无需改动，adapter 替换对 API 层透明。

---

## 已知限制

1. **新浪 K 线**：不支持 5 分钟/15 分钟等分钟级 K 线（仅日/周/月）
2. **新浪无 PB/PE**：这些字段在 `QuoteData` 中为 `None`
3. **新浪限流**：高频访问可能触发 403，建议加缓存
4. **AkShare Python 3.12**：`py_mini_racer` 依赖问题，暂时不可用

---

## 测试覆盖

```
tests/integrations/market_data/
├── test_sina.py     # 单元测试（respx mock）+ 集成测试（skip）
└── test_factory.py   # 工厂逻辑测试

20 passed, 1 skipped (integration test)
```
