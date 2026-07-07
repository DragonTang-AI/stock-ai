"""审计中间件 — P0-F3"""

AUDIT_AUTH_LOGIN = "AUTH_LOGIN"
AUDIT_AUTH_LOGOUT = "AUTH_LOGOUT"
AUDIT_SIGNAL_GENERATE = "SIGNAL_GENERATE"
AUDIT_SIGNAL_EXECUTE = "SIGNAL_EXECUTE"
AUDIT_SIGNAL_REJECT = "SIGNAL_REJECT"
AUDIT_RISK_CHECK_PASS = "RISK_CHECK_PASS"
AUDIT_RISK_CHECK_FAIL = "RISK_CHECK_FAIL"
AUDIT_RISK_LOSS_CIRCUIT_BREAK = "RISK_LOSS_CIRCUIT_BREAK"
AUDIT_COMPLIANCE_FLAG = "COMPLIANCE_FLAG"

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("audit")

def audit_log(
    event: str,
    user_id: int | None = None,
    symbol: str | None = None,
    details: dict[str, Any] | None = None,
    risk_level: str = "LOW",
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "user_id": user_id,
        "symbol": symbol,
        "risk_level": risk_level,
        "details": details or {},
    }
    if risk_level in ("CRITICAL", "HIGH"):
        logger.error(f"[AUDIT:{risk_level}] {json.dumps(entry, ensure_ascii=False)}")
    else:
        logger.info(f"[AUDIT] {json.dumps(entry, ensure_ascii=False)}")


class AuditContext:
    def __init__(self, event: str, user_id=None, symbol=None, details=None, risk_level="LOW"):
        self.event = event
        self.user_id = user_id
        self.symbol = symbol
        self.details = details or {}
        self.risk_level = risk_level
        self.started_at = None
        self.error = None

    def __enter__(self):
        self.started_at = datetime.now(timezone.utc)
        audit_log(self.event, self.user_id, self.symbol, {**self.details, "_entered_at": self.started_at.isoformat()}, self.risk_level)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.error = exc_val
            audit_log(f"{self.event}_ERROR", self.user_id, self.symbol, {**self.details, "error_type": exc_type.__name__, "error_msg": str(exc_val)}, risk_level="HIGH")
        else:
            duration_ms = (datetime.now(timezone.utc) - self.started_at).total_seconds() * 1000 if self.started_at else 0
            audit_log(f"{self.event}_OK", self.user_id, self.symbol, {**self.details, "duration_ms": round(duration_ms, 2)}, self.risk_level)
        return False


class AuditEvent:
    LOGIN = AUDIT_AUTH_LOGIN
    LOGOUT = AUDIT_AUTH_LOGOUT
    SIGNAL_GENERATE = AUDIT_SIGNAL_GENERATE
    SIGNAL_EXECUTE = AUDIT_SIGNAL_EXECUTE
    SIGNAL_REJECT = AUDIT_SIGNAL_REJECT
    RISK_CHECK_PASS = AUDIT_RISK_CHECK_PASS
    RISK_CHECK_FAIL = AUDIT_RISK_CHECK_FAIL
