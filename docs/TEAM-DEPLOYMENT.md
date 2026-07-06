# AI-Stock 协作与部署规范

> 建立时间：2026-07-06  
> 仓库：https://github.com/DragonTang-AI/AI_Stock  
> 生产服务器：root@stockai.dragontang.com

---

## 一、代码仓库现状（2026-07-06 整理后）

| 分支 | 内容 | 用途 |
|------|------|------|
| `main` | **生产代码**（Phase 0 完成） | 权威基准，任何人可从此部署 |
| `production-v1` | 同上（历史备份） | 保留旧历史，无特殊用途 |
| `feat/frontend-ui` | 前端代码 | Marvis 在此开发 |

**旧分支废弃**：`feat/phase6-batch6-prescreen-api` 等 scaffold 分支已废弃，不再使用。

---

## 二、工作目录（本地 worktree）

| 路径 | 分支 | 内容 | 用途 |
|------|------|------|------|
| `backend-prod/` | `origin/main` (detached) | 生产代码 | QClaw 后端开发 |
| `frontend-ui/` | `feat/frontend-ui` | 前端代码 | Marvis 前端开发 |
| `ai-agents/` | `feat/ai-agents` | 旧 Agent 代码 | 参考 |
| `trading-core/` | `feat/trading-core` | 旧交易核心 | 参考 |

---

## 三、协作流程

### QClaw（后端）
```
1. 在 backend-prod/ 开发
2. 测试通过后：git add → git commit → git push origin main
3. 服务器执行：bash /data/stockai/deploy.sh
```

### Marvis（前端）
```
1. 在 frontend-ui/ 开发
2. 测试通过后：git add → git commit → git push
3. 部署：独立流程（Vercel 或手动）
```

### 服务器部署（任何人）
```bash
ssh root@stockai.dragontang.com
bash /data/stockai/deploy.sh
```

---

## 四、生产 API（已有，可对接）

| 端点 | 认证 | 说明 |
|------|------|------|
| `GET /api/v1/selection/recommend` | 无 | 选股推荐 |
| `GET /api/v1/market/quotes` | 无 | 实时行情 |
| `GET /api/v1/market/kline/{symbol}` | 无 | K线数据 |
| `GET /api/v1/portfolio/positions` | JWT | 持仓列表 |
| `GET /api/v1/portfolio/analysis` | JWT | 持仓分析 |
| `GET /api/v1/trading/orders` | JWT | 订单 |
| `POST /api/v1/trading/orders` | JWT | 下单 |
| `GET /api/v1/analysis/diagnose` | JWT | AI诊断 |
| `GET /api/v1/analysis/market/temperature` | 无 | 大盘温度 |

**测试账号**：`analytics_test` / `123456`

---

## 五、Phase 1 计划（QClaw 接下来）

优先级：
1. **P1-1** `/selection/prescreen` — 粗筛候选池
2. **P1-2** `/market/kline` — 历史K线（market.kline_daily）
3. **P1-3** `/market/indicators` — MA/RSI/MACD
4. **P1-4** `/dashboard/overview` — 首页数据整合

---

## 六、重要路径

| 资源 | 路径 |
|------|------|
| 生产后端 | `/data/stockai/backend/` |
| 生产前端 | `/data/stockai/frontend/` |
| 后端日志 | `journalctl -u stockai-api -n 50` |
| 部署脚本 | `/data/stockai/deploy.sh` |
| 契约文档 | `docs/contracts/*.schema.json` |
| 集成报告 | `docs/contracts/INTEGRATION_STATUS.md` |
