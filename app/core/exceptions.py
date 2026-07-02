"""
app/core/exceptions.py — 全局异常类
统一业务异常，不直接暴露技术细节。
"""
from typing import Any


class AppException(Exception):
    """应用层基异常"""

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


# ── 认证相关 ──────────────────────────────────────────────────────────────

class AuthenticationError(AppException):
    """认证失败（用户名/密码错误）"""

    def __init__(self, message: str = "认证失败，用户名或密码错误") -> None:
        super().__init__(
            message=message,
            code="AUTH_FAILED",
            status_code=401,
        )


class TokenExpiredError(AppException):
    """Token 过期"""

    def __init__(self, message: str = "Token 已过期，请重新登录") -> None:
        super().__init__(
            message=message,
            code="TOKEN_EXPIRED",
            status_code=401,
        )


class TokenInvalidError(AppException):
    """Token 无效"""

    def __init__(self, message: str = "Token 无效") -> None:
        super().__init__(
            message=message,
            code="TOKEN_INVALID",
            status_code=401,
        )


# ── 资源相关 ──────────────────────────────────────────────────────────────

class NotFoundError(AppException):
    """资源不存在"""

    def __init__(self, resource: str, identifier: str | int | None = None) -> None:
        msg = f"{resource} 不存在"
        if identifier is not None:
            msg += f"（ID: {identifier}）"
        super().__init__(
            message=msg,
            code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": identifier},
        )


class DuplicateError(AppException):
    """资源重复（唯一约束冲突）"""

    def __init__(self, resource: str, field: str, value: Any) -> None:
        super().__init__(
            message=f"{resource} 已存在（{field}={value}）",
            code="DUPLICATE",
            status_code=409,
            details={"resource": resource, "field": field, "value": value},
        )


# ── 业务相关 ──────────────────────────────────────────────────────────────

class PermissionDeniedError(AppException):
    """权限不足"""

    def __init__(self, message: str = "权限不足") -> None:
        super().__init__(
            message=message,
            code="PERMISSION_DENIED",
            status_code=403,
        )


class ValidationError(AppException):
    """业务校验失败（下单风控等）"""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_FAILED",
            status_code=422,
            details=details,
        )


class InsufficientFundsError(ValidationError):
    """资金不足"""

    def __init__(self, available: float, required: float) -> None:
        super().__init__(
            message="资金不足，无法完成交易",
            details={"available": available, "required": required},
        )


class PositionLimitExceededError(ValidationError):
    """仓位超限"""

    def __init__(self, symbol: str, limit_pct: float, current_pct: float) -> None:
        super().__init__(
            message=f"仓位超限：{symbol} 当前 {current_pct:.1%}，上限 {limit_pct:.1%}",
            details={
                "symbol": symbol,
                "limit_pct": limit_pct,
                "current_pct": current_pct,
            },
        )
