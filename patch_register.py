"""补丁：注册 admin 模型导入与 API 路由到现有应用"""
import os

BACKEND = "/data/stockai/backend"

# 1) models/__init__.py 追加导入
models_init = os.path.join(BACKEND, "app/models/__init__.py")
with open(models_init) as f:
    content = f.read()
if "AdminUser" not in content:
    additions = (
        "from app.models.admin_user import AdminUser  # noqa: F401\n"
        "from app.models.admin_role import AdminRole  # noqa: F401\n"
        "from app.models.operation_log import OperationLog  # noqa: F401\n"
    )
    content = content.rstrip() + "\n" + additions
    with open(models_init, "w") as f:
        f.write(content)
    print("models/__init__.py patched")
else:
    print("models/__init__.py already patched")

# 2) main.py 追加 import 与路由注册
main_path = os.path.join(BACKEND, "app/main.py")
with open(main_path) as f:
    main_content = f.read()
if "app.api.v1.admin" not in main_content:
    imports = (
        "from app.api.v1.admin import auth as admin_auth\n"
        "from app.api.v1.admin import users as admin_users\n"
        "from app.api.v1.admin import roles as admin_roles\n"
        "from app.api.v1.admin import logs as admin_logs\n"
    )
    anchor = "app = FastAPI("
    if anchor in main_content:
        main_content = main_content.replace(anchor, imports + anchor, 1)
    else:
        main_content = main_content.rstrip() + "\n\n" + imports
    routers = (
        "\n\n"
        'app.include_router(admin_auth.router, prefix="/api/v1/admin/auth", tags=["后台认证"])\n'
        'app.include_router(admin_users.router, prefix="/api/v1/admin/users", tags=["后台账号"])\n'
        'app.include_router(admin_roles.router, prefix="/api/v1/admin/roles", tags=["后台角色"])\n'
        'app.include_router(admin_logs.router, prefix="/api/v1/admin/logs", tags=["后台日志"])\n'
    )
    main_content = main_content.rstrip() + routers
    with open(main_path, "w") as f:
        f.write(main_content)
    print("main.py patched")
else:
    print("main.py already patched")
