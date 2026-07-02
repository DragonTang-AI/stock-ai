"""
app/main.py — FastAPI 应用入口
"""
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.exceptions import AppException

from app.api.v1 import auth, market, portfolio, analysis, selection, simulation


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

# ── CORS ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 全局异常处理器 ────────────────────────────────────────────────────────

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """将 AppException 转为标准 JSON 响应"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.to_dict(),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底异常处理（不暴露技术细节）"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误，请稍后重试",
                "details": {},
            },
        },
    )


# ── 路由注册 ─────────────────────────────────────────────────────────────

# v1 API
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(market.router, prefix="/api/v1/market", tags=["行情"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["持仓"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["分析"])
app.include_router(selection.router, prefix="/api/v1/selection", tags=["选股"])
app.include_router(simulation.router, prefix="/api/v1/simulation", tags=["模拟交易"])


# ── 健康检查 ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["系统"])
async def health_check() -> dict[str, str]:
    """健康检查（k8s / 负载均衡探测）"""
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


@app.get("/", tags=["系统"])
async def root() -> dict[str, str]:
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
