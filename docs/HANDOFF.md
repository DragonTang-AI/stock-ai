# HANDOFF — AI-Stock V1 开工交接单

> 当前阶段：V1 / Phase 1 地基搭建  
> 交接对象：Claude Code（建议在 Cursor 内置 Terminal 运行）  
> 当前日期：2026-06-30  
> 原则：先契约、后实现；小步提交；S 级资金路径必须 Opus + 人审。

---

## 1. 本轮已完成

以下文件已经作为项目地基落盘，后续开发必须先读：

| 文件 | 作用 |
|------|------|
| `CLAUDE.md` | 项目宪法，所有 AI 开工前必须完整阅读 |
| `.cursor/rules/000-overview.mdc` | Cursor 全局规则 |
| `.cursor/rules/010-backend.mdc` | 后端分层/异步/DB 规则 |
| `.cursor/rules/020-trading-core.mdc` | S 级交易核心目录锁 |
| `.cursor/rules/030-ai-engine.mdc` | 粗筛层 + 4-Agent 规则 |
| `.cursor/rules/040-frontend.mdc` | uni-app 前端规则 |
| `.cursor/rules/050-tests.mdc` | 测试规则 |
| `AI-Stock-终极架构-Opus定稿.md` | 三期终极架构 Source of Truth |
| `docs/contracts/signal.schema.json` | AI ↔ 交易唯一 Signal 契约 |
| `docs/contracts/trading-data-model.md` | Account / Order / Trade / Position / Snapshot 契约 |
| `docs/deployment/DEPLOYMENT.md` | V1 服务器/域名/部署/Secrets 契约 |
| `docs/integrations/FLASH-RECON-PROMPT.md` | V2：Qlib / VeighNa 侦察模板 |
| `docs/integrations/OPUS-ADAPTER-PROMPT.md` | V2：Qlib / VeighNa adapter 裁决模板 |

已确认关键参数：

- 单票仓位上限：总资产 **15%**
- 单日最大亏损熔断：**5%**
- 初始模拟资金：
  - A 股模拟账户：**1,000,000 CNY**
  - 港股模拟账户：**1,000,000 HKD**
- 依赖管理：**uv**
- V1 市场：**A 股 + 港股**
- V1 不做：实盘自动下单、券商资金打通、Qlib、VeighNa、Kafka、Milvus、MongoDB、K8s
- 部署目标：`117.72.34.228`，主域名 `aistock.dragontang.com`；V1 用 Docker Compose + 宿主机 Nginx + Let's Encrypt
- 仓库为 GitHub private；部署凭证必须用 Deploy Key / GitHub Token，**禁止写入仓库或聊天窗口**

---

## 2. 下一执行者：Claude 桌面端 + Cursor 落地

### 协作方式

本项目不在 Cursor Terminal 中运行 Claude Code，而是使用 **Claude 桌面端** 作为强推理/代码出稿同事，使用 **Cursor** 作为本地落地执行者。

```
Claude 桌面端
  → 阅读/理解契约与任务书
  → 分批输出文件内容、补丁方案、命令清单
  → 不直接假设自己能读写本地仓库或运行命令

Cursor
  → 将 Claude 输出写入本地仓库
  → 运行 uv/pytest/uvicorn 等命令
  → 检查 diff、lint、规则触发与契约一致性
```

### 给 Claude 桌面端的首条指令

```text
你是 AI-Stock 项目的后端/架构实现同事，但你不能直接修改我的本地仓库，也不能直接运行命令。

请先完整阅读以下文件（我会上传或粘贴给你）：
- CLAUDE.md
- AI-Stock-终极架构-Opus定稿.md
- docs/contracts/signal.schema.json
- docs/contracts/trading-data-model.md
- docs/deployment/DEPLOYMENT.md
- docs/HANDOFF.md

然后按 docs/HANDOFF.md 的 Phase 1 任务要求，搭建 FastAPI 后端地基。
注意：app/trading/ 是 S 级路径，本阶段只创建接口/占位，不实现撮合、风控、费用、MarketRule 细节。

请分批输出：
1. 本批要创建/修改的文件清单（每批 ≤ 3-5 个文件）
2. 每个文件的完整内容，或清晰的 unified diff
3. 本批需要我在本地运行的命令
4. 本批验收方式

不要跳步，不要一次性输出整个项目，不要自行假设我已经运行了命令。
```

> 如果 Claude 桌面端不是 Opus，遇到 `app/trading/`、订单状态机、费用、资金更新时，只允许写设计/测试计划，不得写实现。

---

## 3. Phase 1 目标：后端地基（不是业务功能）

本阶段目标是让项目具备可运行的 FastAPI 空壳、基础配置、数据库/Redis 连接、迁移框架、测试框架和目录边界。

**本阶段不实现：**

- 不实现真实撮合
- 不实现 AI Agent 推理
- 不接 AkShare / Tushare
- 不接 Qlib / VeighNa
- 不接实盘
- 不写前端

---

## 4. Phase 1 建议任务拆分

### Step 1：Python / uv / 项目骨架

创建或更新：

```text
pyproject.toml
.python-version              # 如项目需要，可设 3.12
app/__init__.py
app/main.py
app/core/__init__.py
app/core/config.py
app/core/logging.py
app/core/exceptions.py
tests/__init__.py
tests/conftest.py
```

要求：

- Python 3.12
- 依赖管理用 uv
- FastAPI 0.115+
- Pydantic Settings 管理环境变量
- `GET /health` 返回基础健康状态
- `app/main.py` 包含 lifespan 占位，不写业务逻辑

建议依赖：

```text
fastapi
uvicorn[standard]
pydantic-settings
sqlalchemy
asyncpg
alembic
redis
celery
python-jose[cryptography] 或 pyjwt
passlib[bcrypt] 或 argon2-cffi
pytest
pytest-asyncio
httpx
testcontainers[postgresql]
```

### Step 2：数据库 / Redis 基础连接

创建或更新：

```text
app/core/database.py
app/core/redis.py
alembic.ini
alembic/env.py
alembic/versions/.gitkeep
```

要求：

- SQLAlchemy 2.0 async engine/session
- 禁止同步 Session
- Alembic 能读取 `DATABASE_URL`
- Redis 连接池从 `REDIS_URL` 初始化
- 不在 import 阶段主动连接外部服务，连接放 lifespan / dependency 中

### Step 3：基础 schema / contracts 代码占位

创建：

```text
app/schemas/__init__.py
app/schemas/signals.py
app/schemas/common.py
```

要求：

- `app/schemas/signals.py` 必须与 `docs/contracts/signal.schema.json` 对齐
- 先定义 Pydantic model / Enum，不需要接交易逻辑
- action 使用 5 值：`BUY` / `ADD` / `HOLD` / `REDUCE` / `SELL`
- market 使用：`A` / `HK`
- currency 使用：`CNY` / `HKD`

### Step 4：ORM 模型空壳（只落契约字段，不写业务）

创建：

```text
app/models/__init__.py
app/models/base.py
app/models/user.py
app/models/account.py
app/models/order.py
app/models/position.py
app/models/trade.py
app/models/equity_snapshot.py
app/models/report.py
```

要求：

- 字段按 `docs/contracts/trading-data-model.md` 对齐
- 金额 `DECIMAL(20,4)`
- 时间 `TIMESTAMPTZ`
- 主键 UUID
- schema 按 `auth` / `trading` / `market` / `analysis`
- 只写模型定义，不写撮合/资金更新逻辑

### Step 5：API 路由空壳

创建：

```text
app/api/__init__.py
app/api/v1/__init__.py
app/api/v1/router.py
app/api/v1/health.py
app/api/v1/auth.py
app/api/v1/market.py
app/api/v1/analysis.py
app/api/v1/portfolio.py
app/api/v1/simulation.py
app/api/v1/dashboard.py
app/api/v1/websocket.py
```

要求：

- 路由层保持 thin
- 除 `/health` 外，其余可先返回 `501 Not Implemented` 风格响应
- 不在 api 层操作 DB
- 预留 OpenAPI tags

### Step 6：目录占位（明确未来边界）

创建：

```text
app/services/__init__.py
app/selection/__init__.py
app/selection/prescreen.py
app/selection/factors.py
app/agents/__init__.py
app/agents/orchestrator.py
app/trading/__init__.py
app/trading/adapters/__init__.py
app/trading/adapters/base.py
app/tasks/__init__.py
```

要求：

- `selection/prescreen.py` 只写接口/注释：V1 轻量因子粗筛，V2 Qlib 替换内部实现
- `agents/orchestrator.py` 只写模块说明，不调用 LLM
- `trading/adapters/base.py` 只写 V2 adapter 协议草案，不实现实盘
- `app/trading/market_rule.py`、`matching_engine.py`、`risk_control.py`、`fee_calculator.py` **本阶段不要实现**，除非明确切到 Opus 并单独执行 S 级任务

### Step 7：Docker Compose 基础环境

创建：

```text
Dockerfile
docker-compose.yml
.env.example
```

要求：

- 服务：api、postgres、redis、worker、beat（worker/beat 可先占位）
- PostgreSQL 16
- Redis 7
- `.env.example` 不含真实密钥
- 默认环境变量包含：
  - `IS_AUDIT_MODE=true`
  - `DATABASE_URL`
  - `REDIS_URL`
  - `JWT_SECRET`
  - `JWT_EXPIRE_MINUTES`
  - `MAX_POSITION_PCT=0.15`
  - `DAILY_LOSS_CIRCUIT_PCT=0.05`
  - `PAPER_INITIAL_CASH_CNY=1000000`
  - `PAPER_INITIAL_CASH_HKD=1000000`

### Step 8：最小测试

创建：

```text
tests/test_health.py
tests/test_signal_schema.py
```

要求：

- `test_health.py` 验证 `/health` 可用
- `test_signal_schema.py` 至少验证：
  - Signal action 5 值
  - A→CNY、HK→HKD
  - `suggested_position_pct <= 0.15`
  - 示例 Signal 可被 Pydantic model 接受
- 不依赖真实外部 API

---

## 5. Phase 1 验收标准

Cursor 将 Claude 桌面端输出落地后，至少满足：

```bash
uv sync
uv run pytest
uv run uvicorn app.main:app --reload
```

并且：

- `GET /health` 返回 200
- 项目能生成 OpenAPI 文档
- Alembic 环境能启动（可不要求已有完整 migration）
- `docs/contracts/signal.schema.json` 与 `app/schemas/signals.py` 无明显字段冲突
- 没有真实密钥、`.env`、券商账号、API key 被写入仓库
- S 级目录没有实现资金/撮合/费用逻辑，只做必要占位

---

## 6. 当前目录归属

| 路径 | 当前主责 | 本阶段要求 |
|------|----------|------------|
| `CLAUDE.md` | 人工审批 | 不改，除非明确要求 |
| `.cursor/rules/` | Cursor | 不改，除非明确要求 |
| `docs/contracts/` | 人工审批 + Cursor | 本阶段只读；如发现契约问题先汇报 |
| `app/core/` | Claude 桌面端出稿 + Cursor 落地 | 可实现 |
| `app/api/` | Claude 桌面端出稿 + Cursor 落地 | 可实现薄路由 |
| `app/models/` | Claude 桌面端出稿 + Cursor 落地 | 可实现 ORM 字段 |
| `app/schemas/` | Claude 桌面端出稿 + Cursor 落地 | 可实现 Pydantic model |
| `app/services/` | Claude 桌面端出稿 + Cursor 落地 | 只建空壳 |
| `app/selection/` | Opus 出稿 + Cursor 落地 | 本阶段只建占位 |
| `app/agents/` | Opus 出稿 + Cursor 落地 | 本阶段只建占位 |
| `app/trading/` | Opus 出稿 + 人审 + Cursor 落地 | 本阶段只建 adapter/base 占位，不写 S 级实现 |
| `frontend/` | Cursor | 本阶段不动 |

---

## 7. Claude 桌面端与 Cursor 执行纪律

1. Claude 每批输出前先说明将创建/修改哪些文件。
2. 单批输出 ≤ 3-5 文件；大任务拆小步。
3. Claude 不假设自己能直接改仓库或运行命令；命令只作为清单交给 Cursor 执行。
4. Cursor 落地前先快速检查输出是否越界（尤其 `app/trading/`）。
5. 不要自行 commit；除非用户明确要求。
6. 不要运行破坏性命令：`rm -rf`、`git reset --hard`、删除数据库卷等。
7. 遇到契约冲突，先停下汇报，不要自己改 `docs/contracts/`。
8. 遇到 S 级实现需求，切 Opus 并另开明确任务；当前 Phase 1 只做地基。

---

## 8. 给 Cursor 的后续任务（Claude 输出落地后）

Claude 桌面端分批输出 Phase 1 文件后，Cursor 负责：

- 将文件内容/patch 写入本地仓库
- 运行 `uv sync`、`uv run pytest`、`uv run uvicorn app.main:app --reload`
- Review 文件结构与契约一致性
- 检查 `.cursor/rules` 是否在对应目录触发
- 后续按 Ardot 设计稿实现 `frontend/`
- 与 FastAPI OpenAPI 对齐前端 API client

---

## 9. 后续里程碑（暂不执行）

| 里程碑 | 内容 | 触发条件 |
|--------|------|----------|
| Phase 2 数据管道 | AkShare A/HK 行情接入、入库、缓存 | Phase 1 验收通过 |
| Phase 3 选股大脑 | 粗筛层 + LangGraph 4-Agent | Phase 2 完成 |
| Phase 4 交易引擎 | MarketRule + 撮合 + 风控 + 日结 | 单独 S 级任务，Opus + 人审 |
| Phase 5 前端 | Ardot → Cursor → uni-app | 后端 OpenAPI 稳定 |
| V2 集成 | Qlib / VeighNa / Mini-QMT / 富途 | V1 闭环跑通后 |

---

## 10. 当前状态

- [x] 架构定稿
- [x] CLAUDE.md
- [x] Cursor rules
- [x] Signal 契约
- [x] 交易数据模型契约
- [x] Claude 桌面端 + Cursor Phase 1 HANDOFF
- [ ] Claude 桌面端输出 FastAPI 骨架批次
- [ ] Cursor 落地并验证 FastAPI 骨架
- [ ] Cursor review 骨架

