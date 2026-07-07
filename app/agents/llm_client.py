"""app/agents/llm_client.py — 厂商无关 LLM 客户端

- 超时 / 重试 / 降级模型 fallback
- 无 transport 时报告 unavailable，Agent 走确定性 fallback 不失败
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

Transport = Callable[[str, str, str, float], str]
"""transport(model, system_prompt, user_prompt, timeout_seconds) -> raw_text"""


class LLMUnavailableError(RuntimeError):
    """无法获取 LLM 响应（禁用/超时/解析失败）"""


@dataclass(slots=True)
class LLMInvocation:
    model: str
    attempts: int


def _extract_json_object(raw: str) -> dict:
    """从原始文本中提取第一个平衡的 JSON 对象"""
    start = raw.find("{")
    if start == -1:
        raise ValueError("no_json_object_found")

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(raw)):
        char = raw[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                snippet = raw[start : index + 1]
                parsed = json.loads(snippet)
                if not isinstance(parsed, dict):
                    raise ValueError("json_root_not_object")
                return parsed
    raise ValueError("unbalanced_json_object")


class LLMClient:
    def __init__(
        self,
        *,
        primary_model: str,
        backup_model: str = "",
        timeout_seconds: float = 20.0,
        max_retries: int = 2,
        transport: Transport | None = None,
        enabled: bool = True,
    ) -> None:
        self._primary_model = primary_model
        self._backup_model = backup_model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max(1, max_retries)
        self._transport = transport
        self._enabled = enabled
        self.last_invocation: LLMInvocation | None = None

    def available(self) -> bool:
        return self._enabled and self._transport is not None

    def _models(self) -> list[str]:
        models = [self._primary_model]
        if self._backup_model and self._backup_model != self._primary_model:
            models.append(self._backup_model)
        return models

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict:
        if not self.available():
            raise LLMUnavailableError("llm_disabled_or_no_transport")

        assert self._transport is not None
        last_error: Exception | None = None
        for model in self._models():
            for attempt in range(1, self._max_retries + 1):
                try:
                    raw = self._transport(
                        model,
                        system_prompt,
                        user_prompt,
                        self._timeout_seconds,
                    )
                    parsed = _extract_json_object(raw)
                    self.last_invocation = LLMInvocation(model=model, attempts=attempt)
                    return parsed
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    logger.warning(
                        "llm call failed model=%s attempt=%s error=%s",
                        model,
                        attempt,
                        exc,
                    )
        raise LLMUnavailableError("llm_all_models_failed") from last_error


def build_default_client() -> LLMClient:
    """从 settings 构造 LLMClient（transports 会在路由层注入）"""
    from app.agents.transports import build_router_transport

    return LLMClient(
        primary_model=settings.llm_primary_model,
        backup_model=settings.llm_backup_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        transport=build_router_transport(),
        enabled=settings.llm_enabled,
    )
