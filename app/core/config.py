"""
app/core/config.py — 全局配置（使用 Pydantic Settings）
所有配置从环境变量读取，.env 文件不进入版本控制。
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── 应用 ──────────────────────────────────────────────
    app_name: str = "AI-Stock"
    app_version: str = "0.1.0"
    app_description: str = "A股+港股 AI 选股助手 + 模拟交易平台"
    debug: bool = False
    is_audit_mode: bool = True  # V1 默认开启审核模式

    # ── 服务器 ────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    # ── 数据库 ───────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_stock",
        description="Async PostgreSQL 连接串"
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── Redis ────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── JWT ──────────────────────────────────────────────
    jwt_secret: str = Field(default="CHANGE_ME", description="生产环境必须修改")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── LLM ──────────────────────────────────────────────
    llm_primary_api_key: str = ""
    llm_primary_model: str = "claude-sonnet-4-20250514"
    llm_backup_api_key: str = ""
    llm_backup_model: str = "deepseek-chat"

    # ── 数据源 ───────────────────────────────────────────
    akshare_cache_ttl: int = 300  # 秒

    # ── 风控（V1 模拟盘）─────────────────────────────────
    max_position_pct: float = Field(default=0.15, description="单票仓位上限 15%")
    daily_loss_circuit_pct: float = Field(default=0.05, description="单日熔断线 5%")

    # ── CORS ─────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173", "https://app.stockai.dragontang.com"]

    @property
    def cors_regex(self) -> str | None:
        """允许的 Origin（用于生产环境正则匹配）"""
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
