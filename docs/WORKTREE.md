# Git Worktree 协作规范

> 目标：让 Cursor、Claude 桌面端、未来的前端/后端/交易 Agent 并发工作时互不撞车。  
> 原则：主仓库做稳定基线，功能开发全部在独立 worktree 中进行。

---

## 1. 当前仓库与远端

- GitHub: `https://github.com/DragonTang-AI/AI_Stock`
- 主目录：`/Users/admin/Downloads/ai-stock`
- Worktree 根目录：`/Users/admin/Downloads/ai-stock-worktrees`

---

## 2. 分支职责

| 分支 | 目录 | 职责 | 是否直接开发 |
|------|------|------|--------------|
| `main` | `/Users/admin/Downloads/ai-stock` | 稳定基线，只放已确认可追溯的内容 | **否** |
| `dev` | 无固定 worktree | 集成分支，feature 合并后进入这里 | 否 |
| `feat/backend-scaffold` | `ai-stock-worktrees/backend-scaffold` | FastAPI / DB / Redis / Docker / 后端骨架 | 是 |
| `feat/frontend-ui` | `ai-stock-worktrees/frontend-ui` | uni-app / Ardot 落地 / 图表 / 前端联调 | 是 |
| `feat/ai-agents` | `ai-stock-worktrees/ai-agents` | 粗筛层 / LangGraph / Agent 编排 | 是 |
| `feat/trading-core` | `ai-stock-worktrees/trading-core` | S 级交易核心 / MarketRule / 撮合 / 风控 | 是，但需 Opus + 人审 |

当前 worktree：

```text
/Users/admin/Downloads/ai-stock                             main
/Users/admin/Downloads/ai-stock-worktrees/backend-scaffold  feat/backend-scaffold
/Users/admin/Downloads/ai-stock-worktrees/frontend-ui       feat/frontend-ui
/Users/admin/Downloads/ai-stock-worktrees/ai-agents         feat/ai-agents
/Users/admin/Downloads/ai-stock-worktrees/trading-core      feat/trading-core
```

---

## 3. 日常开发流程

### 3.1 开始任务

1. 进入对应 worktree。
2. 确认分支正确：

```bash
git status --short --branch
```

3. 从远端同步：

```bash
git fetch origin
git merge --ff-only origin/dev
```

> 如果 `--ff-only` 失败，说明该分支已有独立提交或 dev 已前进，需要人工判断，不要自动 rebase/merge。

### 3.2 开发中

- 单轮改动 ≤ 3-5 文件。
- 同一文件同一时刻只允许一个 Agent/工具修改。
- 发现需要改其它 worktree 负责目录时，先写入 `docs/HANDOFF.md` 或告知用户，不直接越界。
- S 级目录 `app/trading/` 只在 `feat/trading-core` worktree 中实现。

### 3.3 提交

提交格式：

```text
type(scope): message
```

type ∈ `feat` / `fix` / `refactor` / `test` / `docs` / `chore`

示例：

```bash
git add app/core app/main.py tests/test_health.py
git commit -m "feat(api): add FastAPI health scaffold"
git push
```

> 未经用户明确要求，不要由 AI 主动 commit。用户要求提交时，必须先展示 `git status` 和将被提交的范围。

### 3.4 合并

合并顺序：

```text
feat/* → dev → main
```

- `feat/*` 合并到 `dev`：功能完成、测试通过、无契约冲突。
- `dev` 合并到 `main`：阶段性稳定版本。
- `feat/trading-core` 合并前必须额外满足：
  - Opus 实现或审查
  - 边界测试 + 并发对账测试
  - 人工逐行审查
  - PR/提交说明标明 S 级改动范围

---

## 4. 目录归属

| 路径 | 主责 worktree | 其它 worktree 是否可改 |
|------|---------------|-------------------------|
| `app/core/` | backend-scaffold | 可，但需协调 |
| `app/api/` | backend-scaffold | 可薄改，需协调 |
| `app/models/` | backend-scaffold | 可，但需契约确认 |
| `app/schemas/` | backend-scaffold | 可，但 `signals.py` 必须对齐 `docs/contracts/` |
| `app/services/` | backend-scaffold | 可，但交易相关不得越界 |
| `app/selection/` | ai-agents | 其它只读 |
| `app/agents/` | ai-agents | 其它只读 |
| `app/trading/` | trading-core | 其它只读；Cursor 内不实现 |
| `frontend/` | frontend-ui | 其它只读 |
| `docs/contracts/` | 人工审批 | 修改需先讨论 |
| `CLAUDE.md` | 人工审批 | AI 不得自行修改 |
| `.cursor/rules/` | Cursor/人工 | 修改需同步 CLAUDE.md |

---

## 5. 冲突处理

如果出现冲突：

1. 停止继续生成代码。
2. 记录冲突文件与分支。
3. 判断文件归属，归属方优先解决。
4. 不使用 `git reset --hard`、`git checkout --`、强推等破坏性命令，除非用户明确批准。
5. 合并后必须运行相关测试。

---

## 6. 未跟踪文件策略

主目录中存在一些历史 Battle 文档或其它项目文档，当前**不纳入仓库**，避免污染项目地基。

已纳入首提交的核心文件：

- `CLAUDE.md`
- `.cursor/rules/`
- `AI-Stock-终极架构-Opus定稿.md`
- `docs/HANDOFF.md`
- `docs/contracts/`
- `docs/integrations/`
- `.gitignore`

如需归档旧文档，应另建 `docs/research/archive/` 并由用户确认后再提交。

---

## 7. 新增 worktree 模板

如后续需要新增独立工作线：

```bash
cd /Users/admin/Downloads/ai-stock
git fetch origin
git worktree add -b feat/<name> /Users/admin/Downloads/ai-stock-worktrees/<name> dev
git push -u origin feat/<name>
```

删除已完成 worktree：

```bash
git worktree remove /Users/admin/Downloads/ai-stock-worktrees/<name>
git branch -d feat/<name>
```

> 删除远端分支需人工确认后执行。

