"""
app/api/v1/admin/routes.py — 后台动态路由（按权限返回菜单，异步）
前端 vue-pure-admin 登录后调用 /get-async-routes 获取菜单路由 JSON。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.deps import get_current_admin
from app.core.database import get_db
from app.models.admin_role import AdminRole
from app.models.admin_user import AdminUser

router = APIRouter()

# 菜单定义：meta.required_perm 为访问所需权限（None 表示登录即可见）
_MENUS = [
    {
        "path": "/workspace",
        "name": "Workspace",
        "meta": {"title": "工作台", "icon": "ep:home-filled", "rank": 1},
        "children": [
            {
                "path": "/workspace/index",
                "name": "WorkspaceIndex",
                "meta": {
                    "title": "工作台",
                    "icon": "ep:home-filled",
                    "required_perm": "workspace:view",
                },
            },
        ],
    },
    {
        "path": "/admin",
        "name": "Admin",
        "meta": {"title": "后台管理", "icon": "ep:setting", "rank": 2},
        "children": [
            {
                "path": "/admin/user/index",
                "name": "AdminUser",
                "meta": {
                    "title": "账号管理",
                    "icon": "ep:user",
                    "required_perm": "users:manage",
                },
            },
            {
                "path": "/admin/role/index",
                "name": "AdminRole",
                "meta": {
                    "title": "角色管理",
                    "icon": "ep:lock",
                    "required_perm": "roles:manage",
                },
            },
            {
                "path": "/admin/log/index",
                "name": "AdminLog",
                "meta": {
                    "title": "操作日志",
                    "icon": "ep:document",
                    "required_perm": "logs:view",
                },
            },
        ],
    },
    {
        "path": "/backtest",
        "name": "Backtest",
        "meta": {
            "title": "回测追踪",
            "icon": "ep:data-analysis",
            "rank": 3,
            "required_perm": "backtest:view",
        },
        "children": [],
    },
    {
        "path": "/picks",
        "name": "Picks",
        "meta": {
            "title": "每日推荐",
            "icon": "ep:star",
            "rank": 4,
            "required_perm": "picks:view",
        },
        "children": [],
    },
    {
        "path": "/schedule",
        "name": "Schedule",
        "meta": {
            "title": "调度监控",
            "icon": "ep:alarm-clock",
            "rank": 5,
            "required_perm": "schedule:view",
        },
        "children": [],
    },
    {
        "path": "/customers",
        "name": "Customers",
        "meta": {
            "title": "用户管理",
            "icon": "ep:user-filled",
            "rank": 6,
            "required_perm": "customers:view",
        },
        "children": [
            {
                "path": "/customers/list",
                "name": "CustomerList",
                "meta": {"title": "用户列表", "icon": "ep:list", "required_perm": "customers:view"},
            },
            {
                "path": "/customers/stats",
                "name": "CustomerStats",
                "meta": {"title": "用户统计", "icon": "ep:data-line", "required_perm": "customers:view"},
            },
            {
                "path": "/customers/detail",
                "name": "CustomerDetail",
                "meta": {"title": "用户详情", "icon": "ep:view", "showLink": False, "required_perm": "customers:view"},
            },
        ],
    },
    {
        "path": "/agents",
        "name": "Agents",
        "meta": {
            "title": "Agent监控",
            "icon": "ep:robot",
            "rank": 7,
            "required_perm": "agents:view",
        },
        "children": [
            {
                "path": "/agents/overview",
                "name": "AgentOverview",
                "meta": {"title": "总览", "icon": "ep:data-board", "required_perm": "agents:view"},
            },
            {
                "path": "/agents/list",
                "name": "AgentList",
                "meta": {"title": "交易员列表", "icon": "ep:list", "required_perm": "agents:view"},
            },
            {
                "path": "/agents/sessions",
                "name": "AgentSessions",
                "meta": {"title": "雇佣会话", "icon": "ep:connection", "required_perm": "agents:manage"},
            },
            {
                "path": "/agents/detail",
                "name": "AgentDetail",
                "meta": {"title": "交易员详情", "icon": "ep:view", "showLink": False, "required_perm": "agents:view"},
            },
        ],
    },
    {
        "path": "/login-logs",
        "name": "LoginLogs",
        "meta": {"title": "登录日志", "icon": "ep:monitor", "rank": 9},
        "children": [
            {
                "path": "/login-logs/list",
                "name": "LoginLogList",
                "meta": {
                    "title": "登录日志",
                    "icon": "ep:monitor",
                    "required_perm": "customers:view",
                },
            },
        ],
    },
    {
        "path": "/operation-logs",
        "name": "OperationLogs",
        "meta": {"title": "操作日志", "icon": "ep:document", "rank": 10},
        "children": [
            {
                "path": "/operation-logs/list",
                "name": "OperationLogList",
                "meta": {
                    "title": "操作日志",
                    "icon": "ep:document",
                    "required_perm": "dashboard:view",
                },
            },
        ],
    },
    {
        "path": "/feedbacks",
        "name": "Feedbacks",
        "meta": {"title": "用户反馈", "icon": "ep:chat-dot-round", "rank": 11},
        "children": [
            {
                "path": "/feedbacks/list",
                "name": "FeedbackList",
                "meta": {
                    "title": "用户反馈",
                    "icon": "ep:chat-dot-round",
                    "required_perm": "customers:view",
                },
            },
        ],
    },
    {
        "path": "/broadcasts",
        "name": "Broadcasts",
        "meta": {"title": "广播通知", "icon": "ep:notification", "rank": 12},
        "children": [
            {
                "path": "/broadcasts/list",
                "name": "BroadcastList",
                "meta": {
                    "title": "播报管理",
                    "icon": "ep:notification",
                    "required_perm": "broadcasts:view",
                },
            },
        ],
    },
    {
        "path": "/points",
        "name": "Points",
        "meta": {"title": "积分管理", "icon": "ep:coin", "rank": 13, "required_perm": "points:view"},
        "children": [
            {
                "path": "/points/list",
                "name": "PointsList",
                "meta": {"title": "积分管理", "icon": "ep:coin", "required_perm": "points:view"},
            },
        ],
    },
    {
        "path": "/watchlists",
        "name": "Watchlists",
        "meta": {"title": "自选管理", "icon": "ep:star", "rank": 14, "required_perm": "watchlists:view"},
        "children": [
            {
                "path": "/watchlists/list",
                "name": "WatchlistList",
                "meta": {"title": "自选管理", "icon": "ep:star", "required_perm": "watchlists:view"},
            },
        ],
    },
    {
        "path": "/equity",
        "name": "Equity",
        "meta": {"title": "权益曲线", "icon": "ep:trend-charts", "rank": 15, "required_perm": "equity:view"},
        "children": [
            {
                "path": "/equity/list",
                "name": "EquityList",
                "meta": {"title": "权益曲线", "icon": "ep:trend-charts", "required_perm": "equity:view"},
            },
        ],
    },
]

def _has_perm(meta: dict, perms: list[str]) -> bool:
    required = meta.get("required_perm")
    if not required:
        return True
    return required in perms


def _filter_menu(node: dict, perms: list[str]) -> dict | None:
    children = node.get("children") or []
    filtered_children = [
        _filter_menu(c, perms) for c in children if _has_perm(c.get("meta", {}), perms)
    ]
    filtered_children = [c for c in filtered_children if c is not None]
    if filtered_children or _has_perm(node.get("meta", {}), perms):
        out = dict(node)
        if filtered_children:
            out["children"] = filtered_children
        else:
            out.pop("children", None)
        return out
    return None


@router.get("/get-async-routes")
async def get_async_routes(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    role = await db.get(AdminRole, admin.role_id)
    perms = (role.permissions or []) if role else []
    menus = [
        m for m in (_filter_menu(m, perms) for m in _MENUS) if m is not None
    ]
    return {"code": 0, "data": menus, "message": "ok"}
