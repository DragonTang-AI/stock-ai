"""合规拦截中间件 — P0-F3"""
from __future__ import annotations
import inspect
from functools import wraps
from typing import Any, Callable
from app.middleware.audit import (
    AUDIT_COMPLIANCE_FLAG,
    AUDIT_RISK_CHECK_FAIL,
    AUDIT_RISK_CHECK_PASS,
    audit_log,
)

def get_compliance_settings():
    try:
        from app.core.config_compliance import compliance_settings
        return compliance_settings
    except ImportError:
        class _Fallback:
            is_audit_mode = True
            is_live_trading_enabled = False
            ai_hosted_enabled = False
            disclaimer_enabled = True
            disclaimer_text = "⚠️ 模拟收益仅供参考，不构成投资建议。入市有风险，投资需谨慎。"
        return _Fallback()

def compliance_check(action_name: str, risk_level: str = "HIGH"):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            cs = get_compliance_settings()
            if cs.is_audit_mode:
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                audit_log(AUDIT_COMPLIANCE_FLAG, details={"action": action_name, "reason": "IS_AUDIT_MODE=True 审核模式，拦截执行", "function": func.__name__}, risk_level=risk_level)
                raise PermissionError(f"[审核模式] {action_name}被拦截。如需执行，请关闭审核模式。")
            if action_name in ("提交实盘订单", "开启AI托管") and not cs.is_live_trading_enabled:
                audit_log(AUDIT_COMPLIANCE_FLAG, details={"action": action_name, "reason": "IS_LIVE_TRADING_ENABLED=False，实盘未开启"}, risk_level="CRITICAL")
                raise PermissionError("[合规] 实盘交易功能暂未开放，当前仅支持模拟交易。")
            audit_log(AUDIT_RISK_CHECK_PASS, details={"action": action_name, "function": func.__name__}, risk_level="LOW")
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            cs = get_compliance_settings()
            if cs.is_audit_mode:
                audit_log(AUDIT_COMPLIANCE_FLAG, details={"action": action_name, "reason": "IS_AUDIT_MODE=True", "function": func.__name__}, risk_level=risk_level)
                raise PermissionError(f"[审核模式] {action_name}被拦截。")
            audit_log(AUDIT_RISK_CHECK_PASS, details={"action": action_name, "function": func.__name__}, risk_level="LOW")
            return func(*args, **kwargs)

        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
    return decorator

def check_signal_compliance(signal: dict) -> tuple[bool, str]:
    cs = get_compliance_settings()
    if cs.is_audit_mode:
        return False, "审核模式(IS_AUDIT_MODE=True)，Signal不执行"
    action = signal.get("action", "")
    if action in ("BUY", "ADD") and not cs.is_live_trading_enabled:
        return False, "实盘交易未开启(IS_LIVE_TRADING_ENABLED=False)"
    source = signal.get("source", "")
    if source == "committee_agent" and not cs.ai_hosted_enabled:
        return False, "AI托管未开启(AI_HOSTED_ENABLED=False)"
    min_conf = getattr(cs, "min_confidence_for_action", 60)
    confidence = signal.get("confidence", 0)
    if action in ("BUY", "ADD") and confidence < min_conf:
        return False, f"置信度{confidence}<{min_conf}，低于最低要求"
    return True, ""

def get_disclaimer() -> str:
    cs = get_compliance_settings()
    return cs.disclaimer_text if cs.disclaimer_enabled else ""
