"""
app/main.py — FastAPI 应用入口
"""
import asyncio
import logging

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.exceptions import AppException

from app.api.v1 import auth, market, portfolio, analysis, selection, simulation, watchlist, trading, hosted, extra, broadcast


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    # ── 启动 ────────────────────────────────────────────
    print(f"[{settings.app_name}] 启动中...")
    await init_db()
    print(f"[{settings.app_name}] 数据库初始化完成")

    # 启动 AI托管定时调度（后台循环，随服务启停）
    hosted_scheduler_task = asyncio.create_task(_hosted_scheduler_loop())
    print(f"[{settings.app_name}] AI托管调度已启动")
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
# [P1 dedup] app.include_router(trading.router, prefix="/api/v1/trading", tags=["交易"])
app.include_router(hosted.router, prefix="/api/v1/hosted", tags=["AI托管"])
app.include_router(extra.router, prefix="/api/v1", tags=["扩展"])
app.include_router(broadcast.router, prefix="/api/v1/broadcast", tags=["每日播报"])


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


# ── AI托管定时调度循环 ──────────────────────────────────────────────────

logger = logging.getLogger(__name__)


async def _hosted_scheduler_loop() -> None:
    """AI托管调度循环：每隔固定时间运行一次选股 + 自动交易"""
    from app.tasks.hosted_scheduler import run_hosted_signal_processor
    await asyncio.sleep(30)  # 首次延迟，避免启动即重负载
    while True:
        try:
            await run_hosted_signal_processor()
        except Exception as e:
            logger.warning(f"[托管调度] 循环异常: {e}")
        await asyncio.sleep(900)  # 每 15 分钟执行一次
