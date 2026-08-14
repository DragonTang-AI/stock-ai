"""
app/admin_main.py — 管理后台独立入口（监听 8011）
仅挂载 admin 模块路由，不启动交易引擎调度器，与 C 端主服务（8000）隔离。
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppException

from app.api.v1.admin import auth as admin_auth
from app.api.v1.admin import users as admin_users
from app.api.v1.admin import roles as admin_roles
from app.api.v1.admin import logs as admin_logs
from app.api.v1.admin import routes as admin_routes

app = FastAPI(
    title=f"{settings.app_name} Admin",
    version=settings.app_version,
    description="StockAI 管理后台 API（独立 8011）",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


app.include_router(admin_auth.router, prefix="/api/v1/admin/auth", tags=["后台认证"])
app.include_router(admin_users.router, prefix="/api/v1/admin/users", tags=["后台账号"])
app.include_router(admin_roles.router, prefix="/api/v1/admin/roles", tags=["后台角色"])
app.include_router(admin_logs.router, prefix="/api/v1/admin/logs", tags=["后台日志"])
app.include_router(admin_routes.router, prefix="/api/v1/admin", tags=["后台路由"])
