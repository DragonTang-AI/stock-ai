# Git Worktree 协作规范（QClaw + Marvis 版）

> 版本：v2.0 | 日期：2026-07-02
> 目标：QClaw × Marvis 双团队并行开发，互不冲突
> 仓库：`https://github.com/DragonTang-AI/stock-ai`

---

## 1. 仓库与目录结构

```
主仓库（QClaw 主会话操作）:
/Users/admin/Downloads/ai-stock备份/ai-stock_Qclaw+Marvis/
  origin: https://github.com/DragonTang-AI/stock-ai
  分支: main（文档/契约/架构定稿）

Worktrees（各分支独立工作）:
/Users/admin/Downloads/ai-stock备份/ai-stock-worktrees_Qclaw+Marvis/
  ├── backend-scaffold/  (feat/backend-scaffold)
  ├── ai-agents/        (feat/ai-agents)
  ├── trading-core/      (feat/trading-core)
  └── frontend-ui/       (feat/frontend-ui)
```

**注意：QClaw 和 Claude+Cursor 是完全独立的两个工程目录，互不干扰。**
- QClaw+Marvis 的仓库：`DragonTang-AI/stock-ai`
- Claude+Cursor 的仓库：`DragonTang-AI/AI_Stock`

---

## 2. 分支职责

| 分支 | Worktree 路径 | 职责 | 主力 | S/A级限制 |
|------|-------------|------|------|----------|
| `main` | 主目录 | 文档/契约/架构定稿 | QClaw | — |
| `feat/backend-scaffold` | worktrees/backend-scaffold | FastAPI骨架/API/DB/Redis/Docker | **QClaw** | Marvis 禁止写 trading/agents |
| `feat/ai-agents` | worktrees/ai-agents | 粗筛层/LangGraph/4-Agent引擎 | **QClaw** | Marvis 禁止碰 |
| `feat/trading-core` | worktrees/trading-core | S级/MarketRule/撮合/风控 | **QClaw** | **仅 Opus + 人审实现** |
| `feat/frontend-ui` | worktrees/frontend-ui | uni-app/图表/前端联调 | **Marvis** | QClaw 仅辅助 |

---

## 3. 日常开发流程

### 3.1 开始任务

```bash
# QClaw：在主仓库 pull 最新
cd "/Users/admin/Downloads/ai-stock备份/ai-stock_Qclaw+Marvis"
git fetch origin
git pull

# 进入对应 worktree
cd "/Users/admin/Downloads/ai-stock备份/ai-stock-worktrees_Qclaw+Marvis/backend-scaffold"
git fetch origin
git merge origin/main   # 从 main 同步最新
```

### 3.2 开发规则

1. **同一文件同一时刻只允许一方修改**（共享文件走 HANDOFF 协议）
2. **每次提交 ≤ 5 个文件**，测试通过即 commit
3. **S 级目录** `app/trading/` 只在 `feat/trading-core` worktree 实现
4. **Marvis 禁止写** `app/trading/`、`app/agents/`、`app/selection/`、`app/core/` 核心
5. **提交后立即 push**，不积压本地改动

### 3.3 提交规范

```
<type>(<scope>): <简短描述>

type: feat | fix | refactor | test | docs | chore
scope: backend | frontend | agents | trading | infra | docs
```

示例：
```bash
git add app/api/v1/auth.py tests/test_auth.py
git commit -m "feat(backend): add auth endpoints (login/logout/refresh)"
git push
```

### 3.4 合并顺序

```
feat/* (各 worktree) → main (主仓库)
```

- `feat/trading-core` 合并前：Opus 实现 + 边界测试 + 并发对账测试 + 人工逐行审
- `feat/frontend-ui` 合并前：QClaw 审阅前端架构 + 确认 API 联调无问题

---

## 4. 协作总线

```
QClaw 主会话
  ↓ 写代码 → commit → push
  ↓ 更新 docs/HANDOFF-QCLAW.md

Marvis 子代理
  ↓ 读取 HANDOFF → 认领任务
  ↓ 写代码 → commit → push
  ↓ 更新 HANDOFF

双方通过 Git + HANDOFF 文件交接，不依赖实时聊天。
```

---

## 5. 冲突处理

1. **同一文件冲突**：先 push 者优先，后 push 者自行解决冲突（保留双方合理改动）
2. **目录归属争议**：查 `docs/BOUNDARY.md`
3. **S 级实现争议**：提交设计文档 → 用户 + Opus 决策
4. **禁止使用** `git reset --hard`、`git push --force`

---

## 6. 新增 / 删除 Worktree

### 新增 Worktree
```bash
cd "/Users/admin/Downloads/ai-stock备份/ai-stock_Qclaw+Marvis"
git worktree add -b feat/<name> \
  "/Users/admin/Downloads/ai-stock备份/ai-stock-worktrees_Qclaw+Marvis/<name>" \
  main
git push -u origin feat/<name>
```

### 删除 Worktree（完成使命后）
```bash
cd "/Users/admin/Downloads/ai-stock备份/ai-stock_Qclaw+Marvis"
git worktree remove "/Users/admin/Downloads/ai-stock备份/ai-stock-worktrees_Qclaw+Marvis/<name>"
git branch -d feat/<name>
git push origin --delete feat/<name>
```
