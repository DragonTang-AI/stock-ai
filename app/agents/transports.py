"""app/agents/transports.py — LLM 传输层（Anthropic / DeepSeek）

- 按 model 名路由到对应 provider
- llm_enabled=False 或无 API Key 时返回 None，走确定性 fallback
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.agents.llm_client import Transport
from app.core.config import settings

logger = logging.getLogger(__name__)

_ANTHROPIC_BASE = "https://api.anthropic.com"
_DEEPSEEK_BASE = "https://api.deepseek.com"
_ANTHROPIC_VERSION = "2023-06-01"


class TransportError(RuntimeError):
    """Provider 调用失败或返回无效 payload"""


def _post_json(url: str, headers: dict[str, str], payload: dict, timeout: float) -> dict:
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise TransportError(f"http_error:{exc}") from exc
    except ValueError as exc:
        raise TransportError(f"invalid_json_body:{exc}") from exc


def anthropic_complete(
    *,
    api_key: str,
    base: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: float,
    max_tokens: int,
) -> str:
    data = _post_json(
        f"{base}/v1/messages",
        {
            "x-api-key": api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout,
    )
    blocks = data.get("content", [])
    text = "".join(
        block.get("text", "")
        for block in blocks
        if isinstance(block, dict) and block.get("type") == "text"
    )
    if not text.strip():
        raise TransportError("empty_anthropic_response")
    return text


def deepseek_complete(
    *,
    api_key: str,
    base: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: float,
    max_tokens: int,
) -> str:
    data = _post_json(
        f"{base}/chat/completions",
        {
            "authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        },
        {
            "model": model,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout,
    )
    choices = data.get("choices", [])
    if not choices or not isinstance(choices, list):
        raise TransportError("empty_deepseek_choices")
    content = choices[0].get("message", {}).get("content", "")
    if not content.strip():
        raise TransportError("empty_deepseek_content")
    return content


_PROVIDERS = {
    "anthropic": anthropic_complete,
    "deepseek": deepseek_complete,
}

_DEFAULT_BASES = {
    "anthropic": _ANTHROPIC_BASE,
    "deepseek": _DEEPSEEK_BASE,
}


@dataclass(slots=True)
class ModelRoute:
    provider: str
    api_key: str
    base: str


def build_router_transport() -> Transport | None:
    """构建 model→provider 路由 transport；无配置时返回 None 走 fallback"""
    if not settings.llm_enabled:
        return None

    routes: dict[str, ModelRoute] = {}

    def _add_route(
        model: str,
        provider: str,
        api_key: str,
        api_base: str,
    ) -> None:
        if api_key:
            base = api_base.rstrip("/") if api_base else _DEFAULT_BASES.get(provider, "")
            routes.setdefault(model, ModelRoute(provider=provider, api_key=api_key, base=base))

    _add_route(
        settings.llm_primary_model,
        settings.llm_provider.lower(),
        settings.llm_primary_api_key,
        settings.llm_api_base,
    )
    _add_route(
        settings.llm_backup_model,
        settings.llm_backup_provider.lower(),
        settings.llm_backup_api_key,
        settings.llm_backup_api_base,
    )

    if not routes:
        logger.warning("llm_enabled=true but no API key configured; staying in fallback mode")
        return None

    max_tokens = settings.llm_max_output_tokens

    def transport(model: str, system_prompt: str, user_prompt: str, timeout: float) -> str:
        route = routes.get(model)
        if route is None:
            raise TransportError(f"no_route_for_model:{model}")
        provider_fn = _PROVIDERS.get(route.provider)
        if provider_fn is None:
            raise TransportError(f"unknown_provider:{route.provider}")
        return provider_fn(
            api_key=route.api_key,
            base=route.base,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout=timeout,
            max_tokens=max_tokens,
        )

    return transport
