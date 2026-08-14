"""初始化后台角色与初始管理员账号（幂等，异步）"""
import asyncio
import secrets
import sys

sys.path.insert(0, "/data/stockai/backend")

from sqlalchemy import select  # noqa: E402

from app.core.database import get_session_factory  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.admin_role import AdminRole  # noqa: E402
from app.models.admin_user import AdminUser  # noqa: E402

ALL_PERMS = [
    "dashboard:view", "picks:view", "picks:refresh", "backtest:view",
    "agents:view", "agents:config", "schedule:view", "schedule:trigger",
    "users:manage", "roles:manage", "logs:view", "monitor:view",
]
OPERATOR_PERMS = [
    "dashboard:view", "picks:view", "picks:refresh", "backtest:view",
    "agents:view", "schedule:view", "schedule:trigger", "monitor:view",
]
VIEWER_PERMS = [
    "dashboard:view", "picks:view", "backtest:view",
    "agents:view", "schedule:view", "monitor:view",
]


async def main() -> None:
    factory = get_session_factory()
    async with factory() as db:
        roles = {}
        for code, name, desc, perms in [
            ("admin", "管理员", "全部权限", ALL_PERMS),
            ("operator", "运营", "运营管理权限", OPERATOR_PERMS),
            ("viewer", "只读", "仅查看", VIEWER_PERMS),
        ]:
            result = await db.execute(select(AdminRole).where(AdminRole.code == code))
            role = result.scalar_one_or_none()
            if role is None:
                role = AdminRole(code=code, name=name, description=desc, permissions=perms)
                db.add(role)
                await db.flush()
                print(f"创建角色: {code}")
            else:
                role.name = name
                role.description = desc
                role.permissions = perms
                print(f"更新角色: {code}")
            roles[code] = role.id
        await db.commit()

        result = await db.execute(select(AdminUser).where(AdminUser.username == "admin"))
        admin = result.scalar_one_or_none()
        if admin is None:
            password = secrets.token_urlsafe(10)
            admin = AdminUser(
                username="admin",
                display_name="超级管理员",
                hashed_password=hash_password(password),
                role_id=roles["admin"],
            )
            db.add(admin)
            await db.commit()
            print(f"ADMIN_CREATED|{password}")
        else:
            print("admin 账号已存在，跳过创建")


if __name__ == "__main__":
    asyncio.run(main())
