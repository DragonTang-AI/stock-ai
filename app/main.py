"""
app/main.py — FastAPI 应用入口
"""
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.exceptions import AppException

from app.api.v1 import auth, market, portfolio, analysis, selection, simulation, watchlist, trading, hosted, events, notifications, broadcast, feedback, metrics


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    # ── 启动 ────────────────────────────────────────────
    print(f"[{settings.app_name}] 启动中...")
    await init_db()
    print(f"[{settings.app_name}] 数据库初始化完成")
    yield
    # ── 关闭 ───────────────────────────────────────────
    print(f"[{settings.app_name}] 关闭中...")
    await close_db()
    print(f"[{settings.app_name}] 数据库连接已关闭")


# ── FastAPI App ──────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 由 nginx 处理，不在 FastAPI 层配置

# ── 全局异常处理器 ────────────────────────────────────────────────────────

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """将 AppException 转为标准 JSON 响应"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "data": None,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": f"服务器内部错误: {str(exc)}",
            "data": None,
        },
    )


# ── 路由注册 ─────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(market.router, prefix="/api/v1/market", tags=["行情"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["持仓"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["分析"])
app.include_router(selection.router, prefix="/api/v1/selection", tags=["选股"])
app.include_router(simulation.router, prefix="/api/v1/simulation", tags=["模拟"])
app.include_router(watchlist.router, prefix="/api/v1/watchlist", tags=["自选股"])
app.include_router(trading.router, prefix="/api/v1/trading", tags=["交易"])
app.include_router(hosted.router, prefix="/api/v1/hosted", tags=["AI托管"])
app.include_router(events.router, prefix="/api/v1", tags=["埋点"])
app.include_router(notifications.router, prefix="/api/v1", tags=["通知"])
app.include_router(broadcast.router, prefix="/api/v1", tags=["播报"])
app.include_router(feedback.router, prefix="/api/v1", tags=["反馈"])
app.include_router(metrics.router, prefix="/api/v1", tags=["监控"])


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }
