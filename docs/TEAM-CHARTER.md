# AI-Stock 团队章程：QClaw × Marvis

> 版本：v1.0 | 日期：2026-07-02
> 状态：**开工契约**，开工前必须全员确认并执行
> 变更：需三方（用户 + QClaw + Marvis）书面同意方可修订

---

## 1. 团队成员与角色定位

| 角色 | 身份 | 类比 | 主要能力 |
|------|------|------|---------|
| **QClaw** | 主开发者（架构大脑） | 原 Claude Code | 架构设计 / 后端核心 / AI引擎 / 测试 / 主动规划 |
| **Marvis** | 副开发者（落地执行） | 原 Cursor | 前端 uni-app / 小改 / Bug修复 / 命令执行 / 联调 |
| **用户** | 产品 Owner + 裁判 | — | 需求决策 / 最终验收 / S级人审 / 合规把关 |

---

## 2. 职责分工矩阵

### 2.1 文件归属（按目录，详见 `BOUNDARY.md`）

```
QClaw 主责（feat/backend-scaffold / feat/ai-agents / feat/trading-core）
├── app/trading/          ← S级，MarketRule/撮合/风控/费用
├── app/agents/           ← A级，LangGraph 4-Agent 引擎
├── app/selection/         ← A级，粗筛层 + 因子打分
├── app/core/             ← A级，配置/安全/数据库/Redis/日志
├── app/api/v1/           ← B级，API 路由（Marvis 可辅助）
├── app/services/          ← B级，业务逻辑
├── alembic/              ← B级，数据库迁移
├── tests/                ← B/C级，pytest（QClaw 主导）
├── scripts/              ← B级，初始化/回测脚本
└── docs/                 ← 全部，架构文档/契约/ADR

Marvis 主责（feat/frontend-ui）
├── frontend/             ← 全部，uni-app 前端
└── app/api/v1/          ← B级，API 路由（辅助 QClaw）

共享（需协调）
├── app/schemas/          ← 双方读写需走 HANDOFF 协议
└── app/models/           ← 双方读写需走 HANDOFF 协议
```

### 2.2 任务风险分级与执行者

| 风险级 | 定义 | 执行规则 |
|--------|------|---------|
| **S 级** | 涉及资金/撮合/风控/费用的代码 | QClaw 出设计+测试 → **Claude Opus 写核心** → 用户人审 |
| **A 级** | 架构/AI引擎/LangGraph/复杂集成 | QClaw 主力，Marvis 不碰 |
| **B 级** | 后端 API/Service/迁移/普通逻辑 | QClaw 主力，Marvis 可辅助 |
| **C 级** | 前端页面/图表/样式/CI脚本 | **Marvis 主力**，QClaw 辅助 |

### 2.3 禁止事项（铁律）

| # | 规则 | 违反者 |
|---|------|--------|
| 1 | Marvis 禁止直接修改 `app/trading/` 任何文件 | Marvis |
| 2 | Marvis 禁止直接修改 `app/agents/` 任何文件 | Marvis |
| 3 | S 级文件：非 Opus 模型禁止写核心实现 | 双方 |
| 4 | 同一文件同一时刻只允许一方修改（除非走 HANDOFF 协议） | 双方 |
| 5 | 禁止在不通知对方的情况下修改共享文件（`schemas/`、`models/`） | 双方 |
| 6 | 禁止向非项目成员泄露资金逻辑/风控细节 | 双方 |

---

## 3. 协作总线

### 3.1 通信机制

```
不依赖聊天互传。协作总线：
1. Git 分支（worktree）— 物理隔离，并行开发
2. docs/HANDOFF-QCLAW.md — 任务交接（完成/阻塞/待办）
3. Git 提交信息 — 小步 commit，每次 ≤ 5 文件
4. CLAUDE.md / docs/TEAM-CHARTER.md — 长期约定
5. docs/BOUNDARY.md — 边界争议时以此为准
```

### 3.2 每日工作节奏

**QClaw（主会话 / worktree 并行）：**
- 主动规划任务 → 在对应 worktree 写代码 → commit → push
- 遇到阻塞 → 更新 `docs/HANDOFF-QCLAW.md` → 告知用户
- S 级任务 → 输出设计方案 → 等待 Opus 实施 → 人审

**Marvis（子代理 sessions_spawn 并行）：**
- 监听 HANDOFF-QCLAW.md 任务队列
- 领取 C/B 级任务 → 在 `feat/frontend-ui` worktree 写代码
- 完成 → 更新 HANDOFF → 通知 QClaw（在共享 memory 中记录）
- 遇到问题 → 记录到 HANDOFF → 等待 QClaw 决策

---

## 4. S/A 级任务处理流程

```
用户下达 S/A 级任务
    ↓
QClaw 评估：
    ├── S 级 → 出「设计文档 + 测试用例」→ 提交到 HANDOFF
    │            等待 Opus 实施 → 用户人审 → QClaw 整合测试
    └── A 级 → QClaw 直接执行（Marvis 禁止介入）
    ↓
QClaw 在对应 worktree 提交代码
    ↓
小步 commit → push → 更新 HANDOFF 状态
```

---

## 5. Git Worktree 分配

| Worktree | 分支 | 主责 | 状态 |
|----------|------|------|------|
| 主目录 | `main` | 文档/契约/架构定稿 | ✅ 活跃 |
| worktrees/backend-scaffold | `feat/backend-scaffold` | FastAPI骨架/API/数据库/Services | 🚧 规划 |
| worktrees/ai-agents | `feat/ai-agents` | LangGraph 4-Agent 引擎 | 🚧 规划 |
| worktrees/trading-core | `feat/trading-core` | 交易引擎/S级/MarketRule | 🚧 规划 |
| worktrees/frontend-ui | `feat/frontend-ui` | uni-app 前端 | 🚧 规划 |

详见：`docs/WORKTREE.md`

---

## 6. 初心提醒（永远不忘）

> **产品目标**：A股 + 港股 AI 选股助手 + 模拟交易平台（V1）
>
> **架构原则**：
> - 信号驱动解耦（AI层 ↔ 交易层通过 Signal JSON 通信）
> - 市场可插拔（MarketRule 抽象，A/港/美股可切换）
> - 模块化单体（V1 单体，V3 按需拆微服务）
>
> **合规红线**：小程序仅分析版；交易动作全在 H5；IS_AUDIT_MODE 从 V1 第一行代码生效
>
> **不做**：NestJS / Kafka / Milvus / 强 RL（详见架构文档）
>
> **使命**：10~12 周内交付 V1 内测版本，跑通「分析 + 模拟 + 看板」闭环

---

## 7. 冲突解决

| 场景 | 解决方式 |
|------|---------|
| 文件归属争议 | 查 `docs/BOUNDARY.md`，有疑义用户裁决 |
| 任务重叠 | 先到先写，后写者更新 HANDOFF |
| S 级实现争议 | 提交设计文档，用户 + Opus 决策 |
| 方向偏离 | 回归架构文档第 6 条初心提醒 |
