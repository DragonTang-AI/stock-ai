"""app/agents — 4-Agent 选股委员会（LangGraph）。

架构：粗筛 → 技术面Agent → 基本面Agent → 舆情Agent → 投委会Agent
- AI 模式：LLM 推理打分（DeepSeek/Anthropic）
- Fallback 模式：确定性因子派生评分（无 LLM 依赖）
"""
from app.agents.orchestrator import run_committee_graph

__all__ = ["run_committee_graph"]
