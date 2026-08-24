import logging
"""
app/api/v1/auth.py — 认证路由
POST /api/v1/auth/login          登录
POST /api/v1/auth/register        注册
POST /api/v1/auth/refresh         刷新 Token
POST /api/v1/auth/logout          登出（前端删除 Token 即可，这里仅占位）
GET  /api/v1/auth/me              当前用户信息
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, NotFoundError, TokenInvalidError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.models.user import User, UserLoginLog
from app.models.points import UserPoints, PointsTransaction
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# ── 注册风控（IP 维度限流，基于 Redis） ──────────────────────────────
import redis.asyncio as aioredis

_register_redis: aioredis.Redis | None = None


def _get_register_redis() -> aioredis.Redis:
    """懒加载 Redis 客户端（容器内 REDIS_URL 指向 redis 服务）"""
    global _register_redis
    if _register_redis is None:
        _register_redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _register_redis


async def _check_register_rate_limit(request: Request) -> None:
    """同一 IP 1 小时内最多允许 5 次注册成功（防批量刷号薅注册积分）"""
    ip = request.client.host if request.client else "unknown"
    key = f"auth:register:ip:{ip}"
    try:
        redis = _get_register_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 3600)
        if count > 5:
            logger.warning(f"注册风控触发: 同IP注册次数超限 ip={ip} count={count}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="注册过于频繁，请稍后再试",
            )
    except HTTPException:
        raise
    except Exception as exc:  # Redis 异常不阻塞注册，仅记录
        logger.warning(f"注册风控检查异常: {exc}")

def _detect_platform(ua: str) -> str:
    u = (ua or "").lower()
    if "iphone" in u or "ipad" in u or "ios" in u:
        return "ios"
    if "android" in u:
        return "android"
    if "electron" in u:
        return "desktop"
    if "windows" in u:
        return "windows"
    if "macintosh" in u or "mac os" in u:
        return "macos"
    return "web"


def _detect_client(ua: str) -> str:
    u = (ua or "").lower()
    if "electron" in u:
        return "desktop"
    if "micromessenger" in u or "wxwork" in u:
        return "wechat"
    if "mobile" in u or "android" in u or "iphone" in u or "ipad" in u:
        return "mobile"
    return "web"


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Dependencies ─────────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 JWT 获取当前用户（依赖）"""
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 格式错误",
        )

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
        )

    return user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """从 JWT 获取当前用户（可选依赖，无 token 时返回 None）"""
    # 手动从 Authorization header 解析 token（避免 OAuth2PasswordBearer 自动 401）
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # 去掉 "Bearer " 前缀
    if not token:
        return None
    try:
        payload = verify_token(token, token_type="access")
        if payload is None:
            return None
        user_id: str | None = payload.get("sub")
        if user_id is None:
            return None
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return None
        return user
    except Exception:
        return None


# ── Routes ───────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    用户登录，返回 access_token + refresh_token。
    前端将 access_token 存入 localStorage，每次请求在 Header 携带：
        Authorization: Bearer <access_token>
    """
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        logger.warning(f"登录失败: 用户名或密码错误 username={body.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning(f"登录失败: 账户禁用 user_id={user.id} username={body.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )

    logger.info(f"用户登录成功 user_id={user.id} username={user.username}")
    # 记录登录日志（活跃统计基础数据）
    ua = (request.headers.get("user-agent") or "")[:500]
    db.add(
        UserLoginLog(
            user_id=user.id,
            ip=request.client.host if request.client else None,
            user_agent=ua,
            platform=_detect_platform(ua),
            client=_detect_client(ua),
            is_register=False,
        )
    )
    await db.commit()
    token_data = {"sub": str(user.id), "username": user.username}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """用户注册（V1 仅支持用户名+密码）"""
    # 注册风控：同 IP 限流
    await _check_register_rate_limit(request)
    # 检查重复
    existing = await db.execute(
        select(User).where(
            (User.username == body.username) | (User.email == body.email)
        )
    )
    if existing.scalar_one_or_none() is not None:
        logger.warning(f"注册失败: 用户名或邮箱已存在 username={body.username} email={body.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名或邮箱已被注册",
        )

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 新用户注册赠送 100 积分
    user_points = UserPoints(
        user_id=user.id,
        balance=100,
        total_earned=100,
        total_spent=0,
    )
    db.add(user_points)
    
    points_tx = PointsTransaction(
        user_id=user.id,
        amount=100,
        balance_after=100,
        tx_type="initial",
        description="注册赠送",
    )
    db.add(points_tx)
    await db.commit()

    # 注册即登录：直接签发 token，前端无需二次登录
    logger.info(f"用户注册成功 user_id={user.id} username={body.username} email={body.email}")
    # 记录注册即登录日志
    ua = (request.headers.get("user-agent") or "")[:500]
    db.add(
        UserLoginLog(
            user_id=user.id,
            ip=request.client.host if request.client else None,
            user_agent=ua,
            platform=_detect_platform(ua),
            client=_detect_client(ua),
            is_register=True,
        )
    )
    await db.commit()
    token_data = {"sub": str(user.id), "username": user.username}
    return RegisterResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    body: RefreshTokenRequest,
) -> RefreshTokenResponse:
    """用 refresh_token 刷新 access_token"""
    payload = verify_token(body.refresh_token, token_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token 无效或已过期",
        )

    user_id: str | None = payload.get("sub")
    username: str | None = payload.get("username")
    if user_id is None or username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token 格式错误",
        )

    token_data = {"sub": user_id, "username": username}
    return RefreshTokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: User = Depends(get_current_user)) -> MessageResponse:
    """
    登出。
    JWT 无状态，前端直接删除本地 Token 即可。
    这里提供接口以支持未来可能的 Token 黑名单机制。
    """
    return MessageResponse(message="登出成功")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """获取当前登录用户信息"""
    return current_user
