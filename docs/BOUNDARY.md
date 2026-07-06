# 文件归属与边界规则

> 版本：v1.0 | 日期：2026-07-02
> 目的：消除 QClaw × Marvis 并行开发时的文件冲突
> 裁决：若边界定义与实际不符，以本文件最新版本为准

---

## 1. 绝对归属（只允许一方修改）

### 1.1 QClaw 独占（Marvis 永远不碰）

| 目录/文件 | 风险级 | 原因 |
|----------|--------|------|
| `app/trading/` | **S** | 资金/撮合/风控/费用，任何实现变更必须 Opus + 人审 |
| `app/agents/` | **A** | LangGraph 引擎核心，架构设计级改动 |
| `app/selection/` | **A** | 粗筛层 + 因子打分，AI 核心逻辑 |
| `app/core/` | **A** | 配置/安全/数据库连接/Redis 客户端核心代码 |
| `app/api/v1/selection.py` | **A** | 选股 API，与 agents 层紧耦合 |
| `app/api/v1/trade*.py` | **S** | 交易 API，资金相关 |
| `app/api/v1/simulation*.py` | **S** | 模拟盘 API，资金相关 |
| `tests/test_trading/` | **S** | 交易引擎测试，必须与实现代码同步 |
| `tests/test_agents/` | **A** | AI 引擎测试 |
| `app/tasks/` | **B/A** | Celery 定时任务（每日选股/播报/清算），AI 逻辑部分 |

### 1.2 Marvis 独占（QClaw 通常不碰）

| 目录/文件 | 风险级 | 说明 |
|----------|--------|------|
| `frontend/` | **C** | uni-app 全部前端代码 |
| `frontend/src/pages/**` | **C** | 页面组件 |
| `frontend/src/components/**` | **C** | 可复用组件（K线图/收益率曲线等） |
| `frontend/src/stores/**` | **C** | Pinia 状态管理 |
| `frontend/src/api/**` | **C** | 前端 API 客户端封装 |
| `frontend/src/utils/**` | **C** | 前端工具函数 |

### 1.3 禁止名单（任何人不得直接实现）

```
app/trading/matching_engine.py     ← S级，只能 Opus + 人审实现
app/trading/market_rule.py         ← S级，只能 Opus + 人审实现
app/trading/risk_control.py        ← S级，只能 Opus + 人审实现
app/trading/adapters/*.py          ← A/S级，需架构评审
app/agents/orchestrator.py          ← A级，LangGraph 核心
app/agents/technical_agent.py      ← A级
app/agents/fundamental_agent.py     ← A级
app/agents/sentiment_agent.py      ← A级
app/agents/committee_agent.py      ← A级
```

---

## 2. 共享区域（需要 HANDOFF 协议）

以下目录为共享区域，双方都需要读写，但必须走 HANDOFF 协议。

### 2.1 共享规则

```
共享文件修改流程：
1. 在 HANDOFF-QCLAW.md 中声明「我要修改 XXX」
2. 等待对方确认无冲突（或 5 分钟无异议视为通过）
3. 修改文件
4. commit 并在 HANDOFF 中标记「已完成 XXX」
```

### 2.2 共享目录

| 目录 | 共享内容 | 常见场景 |
|------|---------|---------|
| `app/schemas/` | Pydantic 模型 | QClaw 定义结构，Marvis 前端调用；前端若需新字段走协议 |
| `app/models/` | SQLAlchemy ORM | QClaw 定义表结构，前端需理解字段时只读 |
| `app/api/v1/auth*.py` | 认证 API | QClaw 写接口，Marvis 前端联调 |
| `app/api/v1/market*.py` | 行情 API | QClaw 写接口，Marvis 前端联调 |
| `app/api/v1/portfolio*.py` | 持仓 API | QClaw 写接口，Marvis 前端联调 |
| `app/api/v1/dashboard*.py` | 看板 API | QClaw 写接口，Marvis 前端联调 |
| `app/api/websocket.py` | WebSocket | QClaw 写核心，Marvis 联调前端订阅 |
| `docker-compose.yml` | 容器编排 | 双方都可能修改，QClaw 主导 |
| `pyproject.toml` | 依赖管理 | 双方都可能添加依赖，QClaw 主导 |

---

## 3. 文档归属

| 文件 | 归属 | 说明 |
|------|------|------|
| `CLAUDE.md` | QClaw 维护 | 项目宪法，修改需三方确认 |
| `docs/TEAM-CHARTER.md` | QClaw 维护 | 团队章程 |
| `docs/BOUNDARY.md` | QClaw 维护 | 边界规则 |
| `docs/HANDOFF-QCLAW.md` | 双方共用 | 任务交接，Marvis 也写 |
| `docs/HANDOFF.md` | 保留（Claude+Cursor 用） | 历史文档 |
| `docs/WORKTREE.md` | QClaw 维护 | Worktree 机制说明 |
| `docs/contracts/*.json` | QClaw 维护 | Signal 契约等，Opus 定稿 |
| `docs/adr/*.md` | QClaw 维护 | 架构决策记录 |
| `.cursor/rules/*.mdc` | 保留（Claude+Cursor 用） | 历史文件 |

---

## 4. Git 分支与 Worktree 归属

| Worktree | 分支 | 归属 | 主力 | 辅助 |
|----------|------|------|------|------|
| 主目录 | `main` | 文档/契约/架构 | QClaw | — |
| `worktrees/backend-scaffold` | `feat/backend-scaffold` | FastAPI骨架/API/DB | **QClaw** | Marvis |
| `worktrees/ai-agents` | `feat/ai-agents` | LangGraph 引擎 | **QClaw** | — |
| `worktrees/trading-core` | `feat/trading-core` | 交易引擎/S级 | **QClaw** | — |
| `worktrees/frontend-ui` | `feat/frontend-ui` | uni-app 前端 | **Marvis** | QClaw |

---

## 5. 冲突预判与处理

| 场景 | 处理 |
|------|------|
| Marvis 需要在共享文件加字段 | 在 HANDOFF 声明 → QClaw 审核 → QClaw 或 Marvis 写入 |
| QClaw 发现前端字段需求 | 在 HANDOFF 声明 → Marvis 领取 → 联调 |
| 双方同时改同一共享文件 | 先 push 者的 commit 为准；后 push 者解决冲突 |
| QClaw 被要求直接写前端 | 可写（技术上有能力），但标注「Marvis 确认后生效」 |
| Marvis 被要求写 backend 逻辑 | 禁止，只能写 `frontend/` 目录 |

---

## 6. 边界速查表

```
我（QClaw）可以写：
✅ backend-scaffold / ai-agents / trading-core worktree 的任何文件
✅ 共享区域的 schemas / models（走协议）
✅ 前端（但主责归 Marvis）
✅ CI/CD / Docker / pyproject.toml

我（QClaw）不能直接写：
❌ frontend/ 目录（主责归 Marvis，除非 Marvis 主动要求）
❌ trading/ 核心实现（S级，只能写设计+测试）
❌ 不经 HANDOFF 协议修改共享文件

Marvis 可以写：
✅ frontend/ 的任何文件
✅ 共享区域的 API 路由联调（Marvis 写 frontend 调用方式）
✅ 共享区域的 WebSocket 前端订阅逻辑
✅ CI 前端构建脚本

Marvis 不能写：
❌ app/trading/ 任何文件
❌ app/agents/ 任何文件
❌ app/selection/ 任何文件
❌ app/core/ 核心实现
❌ app/models/ 表结构定义
❌ 不经 HANDOFF 协议修改共享文件
```
