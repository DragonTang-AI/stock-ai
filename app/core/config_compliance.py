"""
合规配置项 — P0-F3
架构原则: 合规是第一行代码，不是最后补

控制项:
- IS_AUDIT_MODE: 审核模式(仅记录，不实际执行)
- IS_LIVE_TRADING_ENABLED: 实盘交易开关(V1锁死False)
- AI_HOSTED_ENABLED: AI托管开关
- 风控阈值: 单票仓位/日亏熔断
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ComplianceSettings(BaseSettings):
    """合规与风控配置"""

    # ── 模式开关 ──
    is_audit_mode: bool = Field(
        default=True,
        description="审核模式：True=仅记录不执行，False=正常执行"
    )
    is_live_trading_enabled: bool = Field(
        default=False,
        description="实盘交易开关：V1阶段锁死False"
    )
    ai_hosted_enabled: bool = Field(
        default=False,
        description="AI托管开关：用户开启后AI可自动触发交易"
    )

    # ── 风控阈值 ──
    max_position_ratio: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="单票仓位上限（占总资产比例，默认15%）"
    )
    max_sector_concentration: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="单行业集中度上限（默认30%）"
    )
    max_daily_loss_ratio: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="日亏熔断阈值（默认5%，触发后暂停AI托管）"
    )
    max_single_trade_ratio: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="单笔交易上限（占总资产比例，默认5%，超限需二次确认）"
    )
    min_confidence_for_action: int = Field(
        default=60,
        ge=0,
        le=100,
        description="AI触发下单最低置信度（低于此值仅提示不执行）"
    )

    # ── 免责声明 ──
    disclaimer_enabled: bool = Field(
        default=True,
        description="是否在API响应中附加免责声明"
    )
    disclaimer_text: str = Field(
        default="⚠️ 模拟收益仅供参考，不构成投资建议。入市有风险，投资需谨慎。",
        description="免责声明文案"
    )

    model_config = SettingsConfigDict(
        env_prefix="COMPLIANCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


compliance_settings = ComplianceSettings()
