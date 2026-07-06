# 部署契约（V1）

> 状态：V1 部署规划  
> 服务器：117.72.34.228  
> 主域名：aistock.dragontang.com  
> 原则：部署信息可入仓，**密钥与真实凭证禁止入仓**。任何服务器写操作必须经用户确认，并与 Claude / Cursor 协作边界对齐。

---

## 1. 已确认服务器信息

只读探测结果（2026-06-30）：

| 项 | 值 |
|----|----|
| IP | `117.72.34.228` |
| 登录用户 | `root` |
| 系统 | Ubuntu 22.04.5 LTS |
| CPU | 4 核 |
| 内存 | 15Gi |
| 磁盘 | 99G，总剩余约 76G |
| Docker | 已安装 |
| Docker Compose | 已安装 |
| Nginx | 已安装且运行中 |
| Certbot | 已安装 |
| 监听端口 | 22 / 80 / 443 |
| 当前 Docker 容器 | 无运行中容器 |

服务器已有多个 Nginx 站点。AI-Stock 部署时必须**新增独立站点配置**，不得覆盖或破坏现有站点。

---

## 2. 域名规划

采用子域名规划：

| 域名 | 用途 | V1 状态 |
|------|------|---------|
| `aistock.dragontang.com` | 官网 / 入口 / 落地页 | 已解析到服务器 |
| `api.aistock.dragontang.com` | 后端 API | 需添加 A 记录 |
| `admin.aistock.dragontang.com` | 后台管理 | 需添加 A 记录，V1 可先预留 |
| `app.aistock.dragontang.com` | H5 交易版 / 模拟盘 | 需添加 A 记录 |

需要在域名服务商添加：

```text
类型: A
主机记录: api
记录值: 117.72.34.228

类型: A
主机记录: admin
记录值: 117.72.34.228

类型: A
主机记录: app
记录值: 117.72.34.228
```

---

## 3. V1 部署方式

V1 采用：

```text
Docker Compose + Nginx + Let's Encrypt
```

部署目录：

```text
/opt/ai-stock
/opt/ai-stock/shared
/opt/ai-stock/backups
```

推荐结构：

```text
/opt/ai-stock/
├── repo/                 # Git 工作副本（部署用）
├── shared/
│   ├── .env              # 真实生产环境变量（不入仓）
│   ├── nginx/            # 站点配置备份
│   └── logs/
└── backups/
    ├── postgres/
    └── redis/
```

V1 服务：

| 服务 | 说明 |
|------|------|
| `api` | FastAPI 后端 |
| `worker` | Celery worker |
| `beat` | Celery beat 定时任务 |
| `postgres` | PostgreSQL 16，本机 Docker volume 持久化 |
| `redis` | Redis 7，本机 Docker volume 持久化 |
| `nginx` | 宿主机已有 Nginx，负责反代和 HTTPS |

> V1 不上 Kubernetes，不做外部托管数据库。等数据量或可用性需求明确后再评估。

---

## 4. GitHub private 仓库部署策略

当前仓库为 **private**：

```text
https://github.com/DragonTang-AI/AI_Stock
```

服务器拉取代码需要安全凭证，二选一：

| 方式 | 推荐度 | 说明 |
|------|--------|------|
| Deploy Key | 推荐 | 给服务器生成只读 SSH key，仅授权本仓库读取 |
| GitHub Token | 可选 | 需要更谨慎管理权限与过期时间 |

**禁止**：

- 禁止把 deploy key 私钥提交到仓库。
- 禁止把 GitHub token 发给 AI 聊天窗口。
- 禁止把 token 写入 `docs/`、`.env.example` 或提交历史。

后续正式部署时，应由用户在服务器上生成 key，并手动添加到 GitHub 仓库 Deploy keys。

---

## 5. 环境变量与 Secrets

仓库只允许提交 `.env.example`，不允许提交 `.env`。

V1 必需变量：

```env
IS_AUDIT_MODE=true

DATABASE_URL=postgresql+asyncpg://ai_stock:change_me@postgres:5432/ai_stock
REDIS_URL=redis://redis:6379/0

JWT_SECRET=change_me
JWT_EXPIRE_MINUTES=60

LLM_PRIMARY_API_KEY=
LLM_PRIMARY_MODEL=
LLM_BACKUP_API_KEY=
LLM_BACKUP_MODEL=

AKSHARE_CACHE_TTL=300

MAX_POSITION_PCT=0.15
DAILY_LOSS_CIRCUIT_PCT=0.05
PAPER_INITIAL_CASH_CNY=1000000
PAPER_INITIAL_CASH_HKD=1000000
```

后续 V2 可能新增：

```env
TUSHARE_TOKEN=
FUTU_HOST=
FUTU_PORT=
MINI_QMT_PATH=
BROKER_ACCOUNT_ID=
```

---

## 6. Nginx / HTTPS 策略

宿主机 Nginx 负责反向代理：

| 域名 | 目标 |
|------|------|
| `api.aistock.dragontang.com` | `127.0.0.1:<api_port>` |
| `app.aistock.dragontang.com` | H5 前端静态资源或前端容器 |
| `admin.aistock.dragontang.com` | 后台管理前端 |
| `aistock.dragontang.com` | 官网/落地页 |

HTTPS 使用 Certbot / Let's Encrypt。

约束：

- 不覆盖 `/etc/nginx/sites-enabled` 中现有站点。
- 新增 AI-Stock 独立站点配置，例如 `/etc/nginx/sites-available/aistock.dragontang.com`。
- 修改 Nginx 前必须先 `nginx -t`。
- reload 前必须确认测试通过：`systemctl reload nginx`。

---

## 7. 数据持久化与备份

PostgreSQL / Redis 使用 Docker named volumes。

V1 备份策略：

- PostgreSQL：每日 `pg_dump` 到 `/opt/ai-stock/backups/postgres/`
- Redis：如只做缓存可不强备；如承载队列/会话，保留 RDB/AOF 配置
- 备份文件后续可接对象存储（V2）

禁止：

- 禁止在未备份情况下删除 Docker volume。
- 禁止运行 `docker compose down -v`，除非用户明确批准。

---

## 8. Claude / Cursor 协作边界

部署相关任务同样遵循：

```text
Claude 桌面端
  → 产出部署方案、配置模板、命令清单
  → 不假设自己能直接改服务器

Cursor
  → 按用户确认后的步骤落地文件
  → 运行命令并反馈结果

用户
  → 掌握服务器真实密钥、GitHub deploy key、生产 secrets
```

任何服务器写操作（创建目录、写 Nginx 配置、写 `.env`、拉代码、启动容器）都必须在执行前明确说明，并经用户确认。

---

## 9. V1 / V2 / V3 演进

| 阶段 | 部署形态 |
|------|----------|
| V1 | 单机 Docker Compose + 宿主机 Nginx + 本机 PG/Redis |
| V2 | 增加实盘 adapter、Tushare/富途配置、备份策略、监控告警 |
| V3 | 视流量与团队规模评估 K8s、托管数据库、Redis Cluster、Kafka、CDN |

---

## 10. 当前待办

- [ ] 用户添加 `api/admin/app` 三条 DNS A 记录
- [ ] 服务器生成 GitHub Deploy Key（private repo 只读拉取）
- [ ] 后端骨架完成后补 `Dockerfile` / `docker-compose.yml`
- [ ] 生成 `.env.example`
- [ ] 生成 Nginx 站点模板
- [ ] 首次部署前人工确认生产 secrets

