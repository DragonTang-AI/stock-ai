"""
app.schemas.trading — 交易域 API 数据模型
"""
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


# ============== 账户 ==============
class AccountInfo(BaseModel):
    """账户信息"""
    account_id: int
    balance: float = Field(..., description="可用余额")
    frozen: float = Field(..., description="冻结资金")
    total_equity: float = Field(..., description="总资产 = 余额 + 冻结 + 持仓市值")
    market_value: float = Field(..., description="持仓市值")
    profit: float = Field(..., description="总盈亏（相对初始 100000）")
    profit_pct: float = Field(..., description="盈亏比例 %")
    market: str
    created_at: datetime


class AccountResponse(BaseModel):
    """账户响应"""
    success: bool
    data: AccountInfo


# ============== 持仓 ==============
class PositionItem(BaseModel):
    """单只持仓"""
    symbol: str
    name: str
    market: str
    quantity: int
    available: int
    cost_price: float
    cost_amount: float
    market_price: float
    market_value: float
    profit: float
    profit_pct: float
    updated_at: datetime


class PositionListResponse(BaseModel):
    """持仓列表响应"""
    success: bool
    data: List[PositionItem] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict, description="汇总：total_market_value / total_profit / total_profit_pct")


# ============== 下单 ==============
class OrderRequest(BaseModel):
    """下单请求"""
    symbol: str = Field(..., description="股票代码，如 600519.SH 或 sh600519")
    side: str = Field(..., description="buy / sell")
    quantity: int = Field(..., gt=0, description="数量（股，100 整数倍）")
    price: Optional[float] = Field(None, description="限价单价格（市价单可不传，按当前价成交）")
    order_type: str = Field("market", description="market / limit")

    @field_validator("side")
    @classmethod
    def _validate_side(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("buy", "sell"):
            raise ValueError("side 必须是 buy 或 sell")
        return v

    @field_validator("order_type")
    @classmethod
    def _validate_order_type(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("market", "limit"):
            raise ValueError("order_type 必须是 market 或 limit")
        return v

    @field_validator("quantity")
    @classmethod
    def _validate_quantity(cls, v: int) -> int:
        if v % 100 != 0:
            raise ValueError("数量必须是 100 的整数倍（A 股交易单位）")
        return v


class OrderItem(BaseModel):
    """订单详情"""
    id: int
    user_id: int
    account_id: int
    symbol: str
    name: str
    side: str
    order_type: str
    price: float
    quantity: int
    filled_quantity: int
    filled_price: float
    amount: float
    commission: float
    tax: float
    status: str
    reject_reason: str
    created_at: datetime
    filled_at: Optional[datetime]
    canceled_at: Optional[datetime]


class OrderListResponse(BaseModel):
    """订单列表响应"""
    success: bool
    data: List[OrderItem] = Field(default_factory=list)
    total: int = 0


class OrderResponse(BaseModel):
    """单个订单响应"""
    success: bool
    data: Optional[OrderItem] = None
    message: str = ""


# ============== 成交 ==============
class TradeItem(BaseModel):
    """成交详情"""
    id: int
    order_id: int
    symbol: str
    name: str
    side: str
    price: float
    quantity: int
    amount: float
    commission: float
    tax: float
    trade_date: date
    created_at: datetime


class TradeListResponse(BaseModel):
    """成交列表"""
    success: bool
    data: List[TradeItem] = Field(default_factory=list)
    total: int = 0


# ============== 持仓分析 ==============
class PositionScore(BaseModel):
    """单只持仓评分（用于排行）"""
    symbol: str
    name: str
    profit: float
    profit_pct: float
    market_value: float
    weight: float = Field(..., description="占总持仓市值比例")


class PortfolioAnalyticsResponse(BaseModel):
    """持仓分析响应"""
    success: bool
    data: Optional[dict] = None


# ============== 扩展分析 ==============
class EquityPoint(BaseModel):
    """收益率曲线数据点"""
    date: str
    equity: float
    benchmark: float = 0


class EquityCurveResponse(BaseModel):
    """收益率曲线响应"""
    success: bool
    data: List[EquityPoint] = Field(default_factory=list)


class AttributionItem(BaseModel):
    """归因分析项"""
    label: str
    contribution: float
    percentage: float


class AttributionResponse(BaseModel):
    """归因分析响应"""
    success: bool
    data: List[AttributionItem] = Field(default_factory=list)


class DashboardSummary(BaseModel):
    """看板概览"""
    totalReturn: float = 0
    annualizedReturn: float = 0
    beatBenchmark: float = 0
    sharpeRatio: float = 0
    maxDrawdown: float = 0
    winRate: float = 0


class DashboardSummaryResponse(BaseModel):
    """看板概览响应"""
    success: bool
    data: DashboardSummary = Field(default_factory=DashboardSummary)


class StatisticsData(BaseModel):
    """统计指标"""
    winRate: float = 0
    profitLossRatio: float = 0
    maxSingleProfit: float = 0
    maxSingleLoss: float = 0
    sharpeRatio: float = 0
    maxDrawdown: float = 0


class StatisticsResponse(BaseModel):
    """统计指标响应"""
    success: bool
    data: StatisticsData = Field(default_factory=StatisticsData)
