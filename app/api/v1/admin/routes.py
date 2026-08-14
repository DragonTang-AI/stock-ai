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
        "path": "/admin",
        "name": "Admin",
        "meta": {"title": "后台管理", "icon": "ep:setting", "rank": 1},
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
            "rank": 2,
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
            "rank": 3,
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
            "rank": 4,
            "required_perm": "schedule:view",
        },
        "children": [],
    }
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
        out["children"] = filtered_children
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
