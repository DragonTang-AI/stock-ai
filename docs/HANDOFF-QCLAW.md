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
## [2026-07-02 下午] Phase 1 后端生产部署完成 + 前端行情/选股页交付

### 🟢 已完成
| 任务 | 负责人 | 完成时间 | 备注 |
|------|--------|----------|------|
| Git 仓库初始化 | QClaw | 2026-07-02 | DragonTang-AI/stock-ai |
| Worktree 建立 | QClaw | 2026-07-02 | 4 个 worktree |
| 开工契约 v1 | QClaw | 2026-07-02 | TEAM-CHARTER / BOUNDARY / HANDOFF-QCLAW / WORKTREE |
| Phase 1 后端骨架 | QClaw | 2026-07-02 上午 | feat/backend-scaffold commit 99fcc69 |
| **Phase 1 生产部署** | **QClaw** | **2026-07-02 13:06** | **http://stockai.dragontang.com 已上线 ✅** |
| T-M001 uni-app 初始化 | Marvis | 2026-07-02 | TabBar + 登录/行情/选股/持仓/我的 |
| T-M003 前后端联调 | Marvis | 2026-07-02 14:30 | commit 5ad0e99 |
| **T-M004 行情页接入 API** | **Marvis** | **2026-07-02 14:50** | **commit 002d196** |
| **T-M005 选股页 UI + Mock** | **Marvis** | **2026-07-02 15:00** | **commit 44a5acd** |

### 🔴 进行中
| 任务 | 负责人 | 状态 | 备注 |
|------|--------|------|------|
| T-S001 行情 API (AkShare) | QClaw | 0% | feat/backend-scaffold |

### 🟠 待认领
| 任务 | 描述 | 优先级 | 建议 |
|------|------|--------|------|
| T-M006 持仓页 UI | 实现持仓列表 + 模拟交易记录 | P2 | 对接 GET /api/v1/portfolio |
| T-M007 选股页接入真实 API | 替换 src/mock/selection.ts 为 GET /api/v1/selection/recommend | P2 | 等 T-S001 完成 |
| T-M008 行情详情页 | ECharts K 线图 + 模拟交易入口 | P2 | 对接 GET /api/v1/market/kline |

### 🟡 阻塞
| 任务 | 负责人 | 阻塞原因 | 等待 |
|------|--------|----------|------|
| T-M007 选股页接入 API | Marvis | 后端选股路由为 Phase 2 桩 | QClaw 完成 T-S001 |

### ⚠️ 注意事项
- **API 已上线**: http://stockai.dragontang.com/docs
- **前端 dev server**: `cd frontend-ui/frontend && npm run dev:h5`
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

---

### T-M004：行情页接入真实 API

**负责人**: Marvis
**类型**: B 级（Marvis 可独立实现）
**Worktree**: feat/frontend-ui
**完成时间**: 2026-07-02 14:50

**完成标准**:
- 行情页移除硬编码 mockQuotes（8 条）
- `fetchQuotes()` 解包后端 `{success, data}` 响应体，标准化字段
- `fetchKLine()` 同样解包
- 下拉刷新、市场筛选（A股/港股/全部）正常

**修改文件**:
- `frontend/src/api/market.ts` — 新增 `normalizeQuote()` + `MarketApiResponse<T>`
- `frontend/src/pages/market/index.vue` — 移除 mock，修复 `onMounted` 钩子

**Git 提交**: `002d196` feat(frontend): T-M004 行情页接入真实 API

**备注**: 后端 `/api/v1/market/quotes` 当前为 Phase 2 桩（price=0），前端完全就绪

---

### T-M005：选股页 UI + Mock 数据

**负责人**: Marvis
**类型**: B 级（Marvis 可独立实现）
**Worktree**: feat/frontend-ui
**完成时间**: 2026-07-02 15:00

**完成标准**:
- ✅ `src/mock/selection.ts` 提供 10 条推荐数据（格式对齐后端 `GET /api/v1/selection/recommend`）
- ✅ 推荐列表按置信度降序，含金/银/铜排名徽章
- ✅ 点击股票 → `uni.navigateTo` 跳转详情页
- ✅ 下拉刷新触发 Mock 数据重新生成（含仿真延迟）
- ✅ Loading 骨架屏 / Error / Empty 三态覆盖
- ✅ 三维评分条（技术面/基本面/舆情）0-100 可视化

**Mock 数据格式**（对接后端接口）:
```json
{
  "symbol": "600519.SH",
  "name": "贵州茅台",
  "confidence": 0.92,
  "reason": "MACD金叉信号确认...",
  "score": {"technical": 0.92, "fundamental": 0.85, "sentiment": 0.90}
}
```

**修改文件**:
- `frontend/src/mock/selection.ts`（新建）— Mock 数据 + `generateRecommendations()` + `deriveAction()`
- `frontend/src/pages/selection/index.vue`（重写）— 接入 Mock、完整三态 UI、骨架屏

**Git 提交**: `44a5acd` feat(frontend): T-M005 选股页 UI + Mock 数据

**备注**: 后端 T-S001 完成后替换 mock 为 `fetch('/api/v1/selection/recommend')` 即可

---

### T-S001：行情 API 接入 AkShare 真实数据

**负责人**: QClaw
**类型**: A 级（QClaw 主责，需 S级测试）
**Worktree**: feat/backend-scaffold
**完成时间**: 2026-07-02 15:10

**完成标准**:
- ✅ `app/schemas/market.py` — QuoteItem / KLineItem Pydantic Schema
- ✅ `app/services/market.py` — AkShare 封装（异步执行 + Mock 降级）
- ✅ `app/api/v1/market.py` — `/quotes` + `/kline/{symbol}` 真实实现
- ✅ 已部署到生产环境 `http://stockai.dragontang.com`
- ✅ API 测试通过（Mock 数据模式，AkShare 待安装）

**技术细节**:
- AkShare 未安装时自动降级到 Mock 数据（不影响 API 启动）
- `fetch_realtime_quotes()` — 使用 `ak.stock_zh_a_spot_em()` 获取全市场数据
- `fetch_kline()` — 使用 `ak.stock_zh_a_hist()` 获取历史 K 线
- 异步封装：`asyncio.run_in_executor` 避免阻塞事件循环

**Git 提交**:
- `3470ec1` feat(api): T-S001 行情 API 接入 AkShare 真实数据
- `1d6801a` fix(services): 兼容 AkShare 未安装环境，返回 Mock 数据

**生产部署**:
- 代码已通过 GitHub 拉取到 `/data/stockai/backend/`
- API 进程已重启（PID 4033758）
- `/health` 检查通过
- `/api/v1/market/quotes?symbols=600519.SH,000001.SZ` 测试通过

**待办**:
- 在生产服务器安装 AkShare（`pip install --user akshare`）
- 安装后 API 自动切换到真实数据（无需重启）

---

## 9. Phase 2 交付物汇总（进行中）

| 模块 | 文件 | 状态 | 备注 |
|------|------|------|------|
| 行情 Schema | app/schemas/market.py | ✅ | QuoteItem + KLineItem |
| 行情服务 | app/services/market.py | ✅ | AkShare 封装 + Mock 降级 |
| 行情路由 | app/api/v1/market.py | ✅ | /quotes + /kline 真实实现 |
| 选股路由 | app/api/v1/selection.py | 🟡 | Phase 2 桩（待 T-S002） |
| 交易路由 | app/api/v1/portfolio.py | 🟡 | Phase 2 桩（待 T-S003） |

---

## 10. 下一步任务

### 🟠 待认领（QClaw）
| 任务 | 描述 | 优先级 | 建议 |
|------|------|--------|------|
| T-S002 | 选股 API 实现（GET /api/v1/selection/recommend） | P0 | 对接 LangGraph Agent |
| T-S003 | 交易 API 实现（订单下单/查询持仓） | P0 | 需对接交易引擎 |
| T-S004 | 在生产服务器安装 AkShare | P1 | `pip install --user akshare` |

### 🟠 待认领（Marvis）
| 任务 | 描述 | 优先级 | 建议 |
|------|------|--------|------|
| T-M006 | 选股页接入真实 API（替换 Mock） | P1 | 等待 T-S002 完成 |
| T-M007 | 行情页 K 线图表优化（ECharts） | P2 | 可独立进行 |

