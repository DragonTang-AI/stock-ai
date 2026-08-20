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
from app.api.v1.admin import backtest as admin_backtest
from app.api.v1.admin import picks as admin_picks
from app.api.v1.admin import schedule as admin_schedule
from app.api.v1.admin import dashboard as admin_dashboard
from app.api.v1.admin import customers as admin_customers
from app.api.v1.admin import login_logs as admin_login_logs
from app.api.v1.admin import operation_logs as admin_operation_logs
from app.api.v1.admin import feedbacks as admin_feedbacks
from app.api.v1.admin import broadcasts as admin_broadcasts
from app.api.v1.admin import agents as admin_agents
from app.api.v1.admin import workspace as admin_workspace
from app.api.v1.admin import monitor as admin_monitor
from app.api.v1.admin import points as admin_points
from app.api.v1.admin import watchlists as admin_watchlists

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
app.include_router(admin_backtest.router, prefix="/api/v1/admin/backtest", tags=["后台回测"])
app.include_router(admin_picks.router, prefix="/api/v1/admin/picks", tags=["后台推荐"])
app.include_router(admin_schedule.router, prefix="/api/v1/admin/schedule", tags=["后台调度"])
app.include_router(admin_dashboard.router, prefix="/api/v1/admin/dashboard", tags=["后台看板"])
app.include_router(admin_customers.router, prefix="/api/v1/admin/customers", tags=["前端用户"])
app.include_router(admin_login_logs.router, prefix="/api/v1/admin/login-logs", tags=["登录日志"])
app.include_router(admin_operation_logs.router, prefix="/api/v1/admin/operation-logs", tags=["操作日志"])
app.include_router(admin_feedbacks.router, prefix="/api/v1/admin/feedbacks", tags=["用户反馈"])
app.include_router(admin_broadcasts.router, prefix="/api/v1/admin/broadcasts", tags=["广播通知"])
app.include_router(admin_agents.router, prefix="/api/v1/admin/agents", tags=["Agent监控"])
app.include_router(admin_workspace.router, prefix="/api/v1/admin/workspace", tags=["工作台"])
app.include_router(admin_monitor.router, prefix="/api/v1/admin/monitor", tags=["系统监控"])
app.include_router(admin_points.router, prefix="/api/v1/admin/points", tags=["积分管理"])
app.include_router(admin_watchlists.router, prefix="/api/v1/admin/watchlists", tags=["自选管理"])
