# 任务交接协议：QClaw × Marvis

> 版本：v1.0 | 日期：2026-07-02
> 目的：QClaw 与 Marvis 不共享上下文，通过本文件交接任务

---

## 1. 工作模式

**QClaw（主会话 + 多 worktree 并行）：**
- 在 `feat/backend-scaffold` / `feat/ai-agents` / `feat/trading-core` 分别写代码
- 通过 HANDOFF 文件向 Marvis 传递任务
- Marvis 的输出通过 Git push → QClaw pull 到本地审阅

**Marvis（子代理 sessions_spawn 并行）：**
- 监听 HANDOFF 文件的任务队列
- 在 `feat/frontend-ui` worktree 写前端代码
- 通过 Git push → QClaw pull 到本地审阅
- 阻塞时在 HANDOFF 标记状态

---

## 2. HANDOFF 文件格式

```markdown
## [YYYY-MM-DD] 交接状态

### 🔴 进行中
| 任务 | 负责人 | 状态 | 备注 |
|------|--------|------|------|
| FastAPI auth 路由 | QClaw | 80% | 预计今天完成 |
| 登录页面 | Marvis | 待认领 | 见下方详细描述 |

### 🟢 已完成
| 任务 | 负责人 | 完成时间 | 备注 |
|------|--------|----------|------|
| Signal 契约定稿 | QClaw | 2026-07-02 | docs/contracts/signal.schema.json |
| CLAUDE.md 更新 | QClaw | 2026-07-02 | 含 QClaw+Marvis 分工 |

### 🟡 阻塞
| 任务 | 负责人 | 阻塞原因 | 等待 |
|------|--------|----------|------|
| WebSocket 前端订阅 | Marvis | 等待后端 WS 路由 | QClaw 完成 app/api/websocket.py |

### 🟠 待认领
| 任务 | 描述 | 优先级 | 建议 |
|------|------|--------|------|
| 登录页面 | 接入 /api/v1/auth/login，响应式布局 | P1 | 先看 schemas/auth.py |
| 首页行情卡片 | 接入 /api/v1/market/quotes，需 ECharts | P2 | — |
```

---

## 3. 任务描述规范

每个任务在「待认领」或「进行中」必须包含：

```markdown
### [任务ID] 任务名称
**负责人**: QClaw / Marvis
**类型**: S/A/B/C 级（见 TEAM-CHARTER.md）
**Worktree**: feat/backend-scaffold / feat/ai-agents / feat/trading-core / feat/frontend-ui
**涉及文件**:
  - app/schemas/auth.py（新建）
  - app/api/v1/auth.py（新建）
**接口描述**:（如有）
  - GET /api/v1/market/quotes?symbols=600519.SH,000001.SZ
  - Response: 见 docs/contracts/signal.schema.json
**完成标准**:（可测试）
  - pytest tests/test_auth.py 通过
  - curl localhost:8000/api/v1/auth/login 返回 200 + JWT
**阻塞条件**:（如有）
  - 等待：app/schemas/auth.py 定稿
```

---

## 4. 交接流程

### 4.1 QClaw → Marvis 传递任务

```
1. QClaw 在 HANDOFF-QCLAW.md「待认领」区域写入任务描述
2. QClaw 在对应 worktree commit 并 push
3. Marvis 子代理 sessions_spawn 读取 HANDOFF → 认领任务
4. Marvis 在 feat/frontend-ui worktree 写代码
5. Marvis commit → push → 更新 HANDOFF「已完成」区域
6. QClaw pull → 审阅 → 如有问题在 HANDOFF 反馈
```

### 4.2 Marvis → QClaw 反馈

```
1. Marvis 在 HANDOFF「阻塞」区域标记问题 + 等待事项
2. QClaw 主会话处理 → 完成 → 更新 HANDOFF「已完成」
3. Marvis 收到通知 → 继续工作
```

### 4.3 冲突处理

```
同一文件被双方同时修改：
1. 先 push 者优先，后 push 者自行解决冲突
2. 解决方式：保留两者合理改动，冲突标记交给作者裁决
3. 重大冲突：用户 + QClaw 决定
```

---

## 5. 提交信息规范

### QClaw 提交
```
feat(api): add auth endpoints (login/logout/refresh)

BREAKING-CHANGE: 无
关联: HANDOFF #3
涉及文件: app/api/v1/auth.py, app/schemas/auth.py
```

### Marvis 提交
```
feat(frontend): add login page with JWT handling

BREAKING-CHANGE: 无
关联: HANDOFF #3
涉及文件: frontend/src/pages/login.vue, frontend/src/api/auth.ts
```

---

## 6. 当前状态（2026-07-02 下午更新）

```markdown
## [2026-07-02 下午] Phase 1 后端生产部署完成

### 🟢 已完成
| 任务 | 负责人 | 完成时间 | 备注 |
|------|--------|----------|------|
| Git 仓库初始化 | QClaw | 2026-07-02 | DragonTang-AI/stock-ai |
| Worktree 建立 | QClaw | 2026-07-02 | 4 个 worktree |
| 开工契约 v1 | QClaw | 2026-07-02 | TEAM-CHARTER / BOUNDARY / HANDOFF-QCLAW / WORKTREE |
| Phase 1 后端骨架 | QClaw | 2026-07-02 上午 | feat/backend-scaffold commit 99fcc69 |
| **Phase 1 生产部署** | **QClaw** | **2026-07-02 13:06** | **http://stockai.dragontang.com 已上线 ✅** |

### 🔴 进行中
| 任务 | 负责人 | 状态 | 备注 |
|------|--------|------|------|
| — | — | — | — |

### 🟠 待认领
| 任务 | 描述 | 优先级 | 建议 |
|------|------|--------|------|
| uni-app 初始化 + 登录页 | feat/frontend-ui 初始化 Vue 项目，接入 POST /api/v1/auth/login | P1 | 见下方 T-M001 |
| uni-app 首页行情 | TabBar 首页 + ECharts K线图，接入 GET /api/v1/market/quotes | P2 | Phase 2 |

### 🟡 阻塞
| 任务 | 负责人 | 阻塞原因 | 等待 |
|------|--------|----------|------|
| — | — | — | — |

### ⚠️ 注意事项
- **API 已上线**: http://stockai.dragontang.com/docs
- **生产环境 Python**: /usr/bin/python3.12, pip packages 在 /data/stockai/pylocal/
- **手动 uvicorn 已启动**（PID 3952305），需配置 systemd 服务持久化
- **SSL 证书**: 尚未配置，http://stockai.dragontang.com 暂为 HTTP
```

---

## 7. Marvis 待认领任务详细描述

### T-M001：uni-app 项目初始化

**负责人**: Marvis
**类型**: B 级（Marvis 可独立实现）
**Worktree**: feat/frontend-ui
**涉及文件**:（新建）
  - frontend/

**完成标准**:
  - `npm run dev` 启动无报错
  - 访问 localhost:5173 能看到登录页 UI

**步骤**:
1. 在 `ai-stock-worktrees_Qclaw+Marvis/frontend-ui/` 目录初始化 uni-app
   ```bash
   npm create vue@latest frontend -- --typescript
   cd frontend && npm install
   ```
2. 配置 `vite.config.ts` 代理到 `http://localhost:8000`
3. 创建 `src/api/auth.ts` 调用登录接口
4. 创建 `src/pages/login.vue` 登录页（用户名 + 密码输入）
5. 提交：commit -m "feat(frontend): uni-app 初始化 + 登录页 UI"

**接口参考**:
```
POST /api/v1/auth/login
Body: { "username": "...", "password": "..." }
Response: { "access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 1800 }
```

---

### T-M003：前后端联调 - 接入真实登录 API

**负责人**: Marvis
**类型**: B 级（Marvis 可独立实现）
**Worktree**: feat/frontend-ui
**完成时间**: 2026-07-02 14:30

**完成标准**:
- 登录页提交 → 调用 `POST /api/v1/auth/login` → 获得 token
- 登录成功 → `GET /api/v1/auth/me` 拉取用户信息 → 展示用户名 + 邮箱
- "我的"页面每次可见时刷新用户数据

**修改文件**:
- `frontend/.env` — `VITE_API_BASE_URL=http://stockai.dragontang.com/api/v1`
- `frontend/.env.example`（新增）— 配置参考文档
- `frontend/src/api/auth.ts` — `UserInfo` 类型对齐后端字段 (id/email/is_active/created_at)
- `frontend/src/stores/auth.ts` — `handleLogin` 成功后调用 `getCurrentUser()` 拉取完整用户信息
- `frontend/src/pages/mine/index.vue` — `onMounted + onShow` 调用 `getCurrentUser()` 刷新，模板新增 email 显示

**Git 提交**: `5ad0e99` feat(frontend): T-M003 前后端联调 - 接入真实登录 API

**API 验证**（curl 全链路测试通过）:
```
POST /api/v1/auth/register → {id, username, email, is_active, created_at}
POST /api/v1/auth/login   → {access_token, refresh_token, token_type, expires_in}
GET  /api/v1/auth/me     → {id, username, email, is_active, created_at}
POST /api/v1/auth/logout  → {message, success}
```

---

## 8. Phase 1 交付物汇总

| 模块 | 文件 | 状态 | 备注 |
|------|------|------|------|
| 配置 | app/core/config.py | ✅ | Pydantic Settings |
| 数据库 | app/core/database.py | ✅ | async SQLAlchemy |
| 安全 | app/core/security.py | ✅ | JWT + bcrypt |
| 异常 | app/core/exceptions.py | ✅ | 统一异常体系 |
| 用户模型 | app/models/user.py | ✅ | SQLAlchemy ORM |
| Auth Schema | app/schemas/auth.py | ✅ | Pydantic 模型 |
| 认证路由 | app/api/v1/auth.py | ✅ | 5 个端点 |
| 行情路由 | app/api/v1/market.py | ✅ | Phase 2 桩 |
| 持仓路由 | app/api/v1/portfolio.py | ✅ | Phase 2 桩 |
| 分析路由 | app/api/v1/analysis.py | ✅ | Phase 2 桩 |
| 选股路由 | app/api/v1/selection.py | ✅ | Phase 2 桩 |
| 模拟交易路由 | app/api/v1/simulation.py | ✅ | Phase 2 桩 |
| FastAPI 入口 | app/main.py | ✅ | lifespan + CORS |
| 测试 | tests/conftest.py + test_auth.py | ✅ | 11 个用例 |
| Docker | docker-compose.yml + Dockerfile | ✅ | Postgres + Redis |
| 依赖 | pyproject.toml + uv.lock | ✅ | pip/uv 兼容 |

**前置条件**: 需要 Docker 运行 `docker compose up postgres redis -d` 启动 Postgres + Redis
