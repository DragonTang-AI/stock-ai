"""
Signal 协议 — AI 层与交易层之间的唯一接口契约
Version: 1.0.0
Date: 2026-07-03

架构原则:
- AI 层（Agent）输出 Signal，不直接操作撮合
- 交易层（Trading）接收 Signal，执行风控和撮合
- 两层互不 import，通过 API 传递 Signal dict
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────── 类型定义 ───────────────────────────────

class ActionType(str, Enum):
    """交易动作枚举"""
    BUY = "BUY"       # 强烈买入
    ADD = "ADD"       # 加仓（已有持仓时）
    HOLD = "HOLD"     # 持有不动
    REDUCE = "REDUCE" # 减仓
    SELL = "SELL"     # 清仓/卖出


class MarketType(str, Enum):
    """市场类型"""
    A = "A"           # A股
    HK = "HK"         # 港股
    US = "US"         # 美股


class CurrencyType(str, Enum):
    """货币类型"""
    CNY = "CNY"
    HKD = "HKD"
    USD = "USD"


class SignalStatus(str, Enum):
    """Signal 状态"""
    PENDING = "PENDING"           # 待执行
    EXECUTED = "EXECUTED"         # 已执行
    REJECTED = "REJECTED"         # 被风控拒绝
    CANCELLED = "CANCELLED"       # 用户取消
    EXPIRED = "EXPIRED"           # 过期失效


# ─────────────────────────────── 原因码枚举 ──────────────────────────────

class ReasonCode(str, Enum):
    """推荐理由编码（可组合）— 包含 committee agent 所有 reason_code"""

    # ── Committee Agent 原因码（与 orchestrator REASON_CODE_VOCAB 对齐）
    MOMENTUM = "momentum"             # 动量强
    BREAKOUT = "breakout"             # 突破
    OVERSOLD = "oversold"            # 超卖
    OVERBOUGHT = "overbought"         # 超买
    UNDERVALUED = "undervalued"       # 低估
    OVERVALUED = "overvalued"         # 高估
    EARNINGS_BEAT = "earnings_beat"   # 业绩超预期
    EARNINGS_MISS = "earnings_miss"   # 业绩低于预期
    HIGH_ROE = "high_roe"            # 高 ROE
    HIGH_DEBT = "high_debt"          # 高负债
    POSITIVE_NEWS = "positive_news"   # 正面新闻
    NEGATIVE_NEWS = "negative_news"   # 负面新闻
    SECTOR_ROTATION = "sector_rotation"  # 板块轮动
    STOP_LOSS_HIT = "stop_loss_hit"   # 止损触发
    TAKE_PROFIT_HIT = "take_profit_hit"  # 止盈触发

    # ── 扩展：技术面
    TECH_MA_GOLDEN = "TECH_MA_GOLDEN"           # 均线金叉
    TECH_MA_DEAD = "TECH_MA_DEAD"               # 均线死叉
    TECH_RSI_OVERSOLD = "TECH_RSI_OVERSOLD"    # RSI 超卖
    TECH_RSI_OVERBOUGHT = "TECH_RSI_OVERBOUGHT"# RSI 超买
    TECH_MACD_DIVERGE = "TECH_MACD_DIVERGE"    # MACD 背离
    TECH_BOLL_BREAK = "TECH_BOLL_BREAK"        # 布林带突破
    TECH_VOLUME_SPIKE = "TECH_VOLUME_SPIKE"    # 成交量异动
    TECH_TREND_UP = "TECH_TREND_UP"            # 上升趋势
    TECH_TREND_DOWN = "TECH_TREND_DOWN"        # 下降趋势

    # ── 扩展：基本面
    FUND_PE_LOW = "FUND_PE_LOW"                 # PE 低估
    FUND_PE_HIGH = "FUND_PE_HIGH"               # PE 高估
    FUND_PB_LOW = "FUND_PB_LOW"                 # PB 低估
    FUND_PROFIT_GROW = "FUND_PROFIT_GROW"       # 净利润增长
    FUND_ROE_HIGH_EXT = "FUND_ROE_HIGH"        # ROE 高
    FUND_DEBT_LOW_EXT = "FUND_DEBT_LOW"        # 负债率低
    FUND_CASH_RICH = "FUND_CASH_RICH"          # 现金流充裕
    FUND_DIVIDEND_HIGH = "FUND_DIVIDEND_HIGH"  # 高股息

    # ── 扩展：舆情
    SENT_POSITIVE = "SENT_POSITIVE"             # 正面舆情
    SENT_NEGATIVE = "SENT_NEGATIVE"            # 负面舆情
    SENT_NEWS_HOT = "SENT_NEWS_HOT"           # 新闻热点
    SENT_INST_BUY = "SENT_INST_BUY"           # 机构买入评级
    SENT_RESEARCH_BULLISH = "SENT_RESEARCH_BULLISH"  # 研报看多
    SENT_BANNER_PULL = "SENT_BANNER_PULL"     # 公告利好
    SENT_BANNER_BAD = "SENT_BANNER_BAD"       # 公告利空

    # ── 风控
    RISK_STOP_LOSS = "RISK_STOP_LOSS"          # 止损触发
    RISK_TAKE_PROFIT = "RISK_TAKE_PROFIT"      # 止盈触发
    RISK_POSITION_LIMIT = "RISK_POSITION_LIMIT"  # 仓位超限
    RISK_LOSS_LIMIT = "RISK_LOSS_LIMIT"        # 亏损超限


# ─────────────────────────────── Signal 主模型 ────────────────────────────

class Signal(BaseModel):
    """
    Signal — AI 层输出给交易层的唯一数据结构
    
    字段规则：
    - 必须字段：symbol, market, action, confidence
    - 可选字段：带 default=None，在特定 action 下有含义
    """
    
    # ── 核心标识 ──
    signal_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="唯一标识，全局不重复"
    )
    symbol: str = Field(
        ...,
        description="股票代码，含市场后缀，如 600519.SH / 0700.HK"
    )
    symbol_name: str | None = Field(
        default=None,
        description="股票名称（committee agent 使用）"
    )
    market: MarketType = Field(
        ...,
        description="市场类型：A=H股, HK=港股, US=美股"
    )
    
    # ── 交易指令 ──
    action: ActionType = Field(
        ...,
        description="交易动作：BUY/ADD/HOLD/REDUCE/SELL"
    )
    confidence: Annotated[int, Field(ge=0, le=100)] = Field(
        ...,
        description="置信度 0-100，越高越确定"
    )
    
    # ── 价格信号（BUY/SELL 时必填，HOLD 时可省略） ──
    currency: CurrencyType = Field(
        default=CurrencyType.CNY,
        description="计价货币"
    )
    target_price: float | None = Field(
        default=None,
        description="目标价（建议买入/卖出价位）"
    )
    stop_loss: float | None = Field(
        default=None,
        description="止损价（跌破触发止损）"
    )
    take_profit: float | None = Field(
        default=None,
        description="止盈价（涨到触发止盈）"
    )
    
    # ── 推荐理由 ──
    reason_codes: list[ReasonCode] = Field(
        default_factory=list,
        description="推荐理由编码列表（可多选）"
    )
    reasoning: str = Field(
        default="",
        max_length=500,
        description="推荐理由自然语言说明（≤500字）"
    )
    
    # ── 附加信息 ──
    source: str = Field(
        default="committee_agent",
        description="Signal 来源 Agent：technical_agent / fundamental_agent / sentiment_agent / committee_agent"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="附加标签，如 momentum / value / dividend"
    )

    # ── Committee Agent 评分（内部使用，投委会输出）
    agent_scores: AgentScores | None = Field(
        default=None,
        description="三维度 Agent 评分（技术面/基本面/舆情），committee agent 专用"
    )
    
    # ── 元数据 ──
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Signal 生成时间（UTC）"
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Signal 失效时间（UTC），None=永不过期"
    )
    status: SignalStatus = Field(
        default=SignalStatus.PENDING,
        description="Signal 状态"
    )
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """验证股票代码格式"""
        if not v or len(v) < 4:
            raise ValueError(f"股票代码格式无效: {v}")
        return v.upper()
    
    @field_validator("target_price", "stop_loss", "take_profit")
    @classmethod
    def validate_prices(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError(f"价格必须 > 0: {v}")
        return v
    
    def is_expired(self) -> bool:
        """检查 Signal 是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self) -> bool:
        """检查 Signal 是否有效（未过期 + 未执行）"""
        return (
            self.status == SignalStatus.PENDING
            and not self.is_expired()
        )
    
    def to_execute_params(self) -> dict:
        """转换为撮合引擎执行参数"""
        return {
            "symbol": self.symbol,
            "market": self.market.value,
            "action": self.action.value,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "source": self.source,
        }


# ─────────────────────────────── Signal 列表 ──────────────────────────────

class SignalList(BaseModel):
    """Signal 批量响应"""
    signals: list[Signal] = Field(default_factory=list)
    total: int = Field(default=0)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ─────────────────────────────── Signal 执行记录 ──────────────────────────

class SignalExecution(BaseModel):
    """Signal 执行记录（写入审计日志）"""
    signal_id: str
    user_id: int | None = None
    executed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    status: SignalStatus
    reject_reason: str | None = None
    order_id: str | None = None
    executed_price: float | None = None
    executed_quantity: int | None = None


# ─────────────────────────────── Agent 评分 ───────────────────────────────

class AgentScores(BaseModel):
    """三维度 Agent 评分（技术面 / 基本面 / 舆情），committee agent 输出"""
    technical: int = Field(ge=0, le=100, description="技术面评分 0-100")
    fundamental: int = Field(ge=0, le=100, description="基本面评分 0-100")
    sentiment: int = Field(ge=-50, le=50, description="舆情评分 -50~50")


class AgentScore(BaseModel):
    """单 Agent 评分（内部使用，不暴露给交易层）"""
    agent_name: Literal["technical", "fundamental", "sentiment"]
    score: Annotated[int, Field(ge=0, le=100)]
    reasons: list[str] = Field(default_factory=list)
    confidence: Annotated[int, Field(ge=0, le=100)] = Field(default=50)
    
    def to_reason_codes(self) -> list[ReasonCode]:
        """转换为 reason_codes（需按 Agent 类型映射）"""
        codes: list[ReasonCode] = []
        for r in self.reasons:
            try:
                codes.append(ReasonCode(r))
            except ValueError:
                pass
        return codes


class AgentScoreReport(BaseModel):
    """三 Agent 评分报告 → 投委会输入"""
    symbol: str
    market: MarketType
    technical: AgentScore = Field(default_factory=lambda: AgentScore(agent_name="technical", score=50))
    fundamental: AgentScore = Field(default_factory=lambda: AgentScore(agent_name="fundamental", score=50))
    sentiment: AgentScore = Field(default_factory=lambda: AgentScore(agent_name="sentiment", score=50))
    
    @property
    def avg_score(self) -> float:
        return (self.technical.score + self.fundamental.score + self.sentiment.score) / 3
    
    def to_signal(self, action: ActionType, reasoning: str) -> Signal:
        """转换为最终 Signal"""
        return Signal(
            symbol=self.symbol,
            market=self.market,
            action=action,
            confidence=int(self.avg_score),
            reasoning=reasoning,
            source="committee_agent",
        )
