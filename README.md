# AI-Stock Backend（Scaffold）

> Phase 1 阶段：`feat/backend-scaffold` worktree
> 分支：`feat/backend-scaffold`
> 仓库：`https://github.com/DragonTang-AI/stock-ai`

## 快速启动

### 1. 安装依赖

```bash
# 推荐使用 uv（更快）
uv sync

# 或 pip
pip install -e ".[dev]"
```

### 2. 启动基础设施

```bash
docker compose up postgres redis -d
```

### 3. 复制环境变量

```bash
cp .env.example .env
# 编辑 .env，修改 JWT_SECRET 等
```

### 4. 启动 API

```bash
uv run uvicorn app.main:app --reload --port 8000
```

访问：http://localhost:8000/docs（Swagger UI）

### 5. 运行测试

```bash
uv run pytest tests/ -v
```

## 已实现的 API

| 方法 | 路径 | 说明 | 状态 |
|------|------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 | ✅ Phase 1 |
| POST | `/api/v1/auth/login` | 登录，返回 JWT | ✅ Phase 1 |
| POST | `/api/v1/auth/refresh` | 刷新 Token | ✅ Phase 1 |
| POST | `/api/v1/auth/logout` | 登出 | ✅ Phase 1 |
| GET | `/api/v1/auth/me` | 当前用户信息 | ✅ Phase 1 |
| GET | `/api/v1/market/quotes` | 行情报价 | 🔜 Phase 2 |
| GET | `/api/v1/portfolio/positions` | 持仓列表 | 🔜 Phase 2 |
| POST | `/api/v1/simulation/orders` | 下单 | 🔜 Phase 2 |

## 项目结构

```
backend-scaffold/
├── app/
│   ├── main.py              FastAPI 入口 + lifespan
│   ├── core/
│   │   ├── config.py        全局配置（Pydantic Settings）
│   │   ├── database.py      async SQLAlchemy session
│   │   ├── security.py      JWT + bcrypt 工具
│   │   └── exceptions.py    全局异常类
│   ├── api/v1/
│   │   ├── auth.py          认证路由
│   │   ├── market.py        行情路由（Phase 2）
│   │   ├── portfolio.py     持仓路由（Phase 2）
│   │   ├── analysis.py      分析路由（Phase 2）
│   │   ├── selection.py     选股路由（Phase 2）
│   │   └── simulation.py    模拟交易路由（Phase 2）
│   ├── schemas/             Pydantic 模型
│   ├── models/              SQLAlchemy ORM 模型
│   ├── services/            业务逻辑（Phase 2）
│   ├── selection/           粗筛层（Phase 2）
│   ├── agents/              LangGraph 引擎（Phase 2）
│   └── trading/             交易引擎（S级，Opus实现）
├── tests/
│   ├── conftest.py          pytest fixtures
│   └── api/test_auth.py     认证 API 测试
├── docker-compose.yml       Postgres + Redis + API
├── Dockerfile
├── pyproject.toml
└── .env.example
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql+asyncpg://postgres:postgres@localhost:5432/ai_stock` |
| `REDIS_URL` | Redis 连接串 | `redis://localhost:6379/0` |
| `JWT_SECRET` | JWT 密钥（生产必须改） | `CHANGE_ME` |
| `IS_AUDIT_MODE` | 审核模式 | `true` |
