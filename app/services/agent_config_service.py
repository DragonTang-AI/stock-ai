"""
agent_config_service.py — Agent交易员配置查询工具

P1: 统一从 agent_configs 表查询配置，供 engine 层使用。
配置缺失时返回 None，各调用点自行兜底默认值。
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentConfig

# ── 默认值（当配置缺失或未启用时兜底） ──
DEFAULTS = {
    "max_position_pct": 30,         # 百分比，使用时 /100
    "max_position_count": 5,
    "loss_stop_pct": 5,            # 百分比，使用时 /100
    "t1_enabled": True,
    "auto_exec_confidence": 50,
    "max_auto_exec_per_round": 2,
    "signal_interval_min": 3,      # 分钟
    "allocated_capital": 100000,
}


async def get_agent_config(db: AsyncSession, hire_id: int) -> Optional[AgentConfig]:
    """查询单个 hire 的配置，可能为 None"""
    result = await db.execute(
        select(AgentConfig).where(AgentConfig.hire_id == hire_id)
    )
    return result.scalar_one_or_none()
