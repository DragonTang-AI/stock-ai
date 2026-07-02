# CLAUDE.md — AI-Stock 项目宪法

> 本文件是项目的最高行为准则。**任何 AI（Claude Code / Cursor / 其他）在执行任务前必须先完整阅读本文件。**
> 修改本文件 = 修宪，必须经人工（项目负责人）审批，不得由 AI 自行更改。
> 架构依据：`AI-Stock-终极架构-Opus定稿.md`（唯一架构 Source of Truth）。
> 最近更新：2026-06-02 ｜ 当前阶段：**V1 开发**

---

## 0. 一分钟速读（AI 必记）

1. 这是一个 **A股 + 港股** 的 AI 选股 / 模拟交易平台，V1 不做实盘自动下单。
2. 技术栈：**Python 3.12 + FastAPI + SQLAlchemy 2.0(async) + Celery + PostgreSQL 16 + Redis 7 + LangGraph + uni-app(Vue3)**。
3. 选股 = **粗筛层(非 LLM) → 4-Agent 投委会(LLM)**，两层都不能省。
4. AI 层与交易层**只通过 `Signal` JSON 协议通信**，禁止互相 import。
5. 市场差异（A股/港股）**全部收敛在 `MarketRule`**，上层不写 if market == ...。
6. 涉及**资金/订单/撮合/风控**的代码是 **S 级**：强模型 + 测试 + 人工审查，缺一不可。
7. **小步提交**：每次改 ≤ 3-5 文件，测试通过立即 commit。
8. 不确定就停下来问，**禁止自行扩大改动范围 / 自行删除环境或重建**。

---

## 1. 项目定位与边界

- **产品 A（分析版）**：微信小程序，纯信息展示（行情播报 / 选股推荐 / 持仓诊断只读 / 看板），**无任何交易动作**。
- **产品 B（交易版）**：H5 Web App，模拟交易（手动 + AI 托管）/ 看板 / 实盘(V2)。
- 两个产品**共用同一套后端与 AI 引擎**，通过 `IS_AUDIT_MODE` 与前端条件编译区分。
- **V1 范围**：分析 + 模拟盘 + 看板（A股 + 港股）。**V1 不做**：实盘自动下单、券商资金打通（仅占位 UI）。

---

## 2. 技术栈（版本即契约）

| 层 | V1 选型 | 备注 |
|----|---------|------|
| 前端 | uni-app (Vue3 + Vite) + Pinia + ECharts | 一码多端 |
| 后端 | FastAPI 0.115+ | 全异步 |
| ORM | SQLAlchemy 2.0 (async) | 禁用同步 Session |
| 任务 | Celery + Redis | 盘后/定时 |
| Agent | LangGraph 0.3+ | 状态机编排 |
| LLM | Claude Sonnet(主) + DeepSeek/GPT(备) | 运行时调用 |
| 量化 | TA-Lib / pandas-ta | 本地计算，不走 LLM |
| 数据库 | PostgreSQL 16 + pgvector(列预留) | 一库 + schema 隔离 |
| 缓存/队列 | Redis 7 | 缓存/Stream/WS/Session |
| 数据源 | AkShare(首选) → Tushare Pro(升级) | A股；港股 AkShare 基础 |
| 部署 | Docker Compose + Nginx | 单机 |
| 依赖管理 | uv（优先）或 poetry | 锁定版本 |

**V1 明确不用**（未经修宪不得引入）：NestJS、Kafka、Milvus、MongoDB、Qlib、VeighNa、Kubernetes、强化学习框架。
解禁时机见架构文档第 6 节"明确不做"表。

---

## 3. 架构铁律（七条，不可违背）

```
1. 够用即可        不引入还没遇到性能问题的组件
2. 纯 Python 主栈  V1 不引入第二种后端语言
3. 信号驱动解耦    AI 引擎与交易引擎只通过 Signal JSON 通信
4. 模块化单体      单体内按未来微服务边界分目录，不提前拆分
5. 市场可插拔      A股/港股/美股 通过 MarketRule + DataSource + Adapter 适配
6. 资金即红线      涉及钱的代码 = S 级，强模型 + 测试 + 人审
7. 合规前置        审核模式 / 免责声明 / 产品分拆 从第一行代码就在
```

---

## 4. 分层规则（严禁跨层）

```
api (路由, 薄)  →  service (业务逻辑)  →  model (ORM) / 外部适配器
```

- `api/` 层**只做**：参数校验（Pydantic）、调用 service、组装响应。**禁止**在 api 层直接操作 DB 或写业务逻辑。
- `service/` 层：唯一允许进行 DB 操作和业务编排的地方。
- `model/` 层：SQLAlchemy ORM，纯数据定义。
- 所有请求/响应**必须**有对应 Pydantic schema，禁止裸 dict 出入接口。
- 跨模块调用走 service，不直接 import 另一模块的 api 层。

---

## 5. 选股双层架构（V1 核心约定，不可合并）

```
全市场 5000+ 票
   │  ① 粗筛层  app/selection/prescreen.py  （非 LLM，秒级）
   │     pandas-ta 因子打分 + 加权排序 → 候选池
   ▼
Top 30~50（标准候选池，结构化输出）
   │  ② 精选层  app/agents/  （LLM，只看候选池，控成本）
   ▼
技术面 / 基本面 / 舆情 Agent → 投委会 Agent → Top 5 + 置信分 + 理由 + 播报
```

- **粗筛层禁止调用 LLM**；它的存在就是为了让 LLM 不必面对全市场（成本/延迟红线）。
- 粗筛层必须输出**稳定的候选池数据结构**（见 `schemas/`），V2 用 Qlib 替换其内部实现时，**精选层不得改动**。
- 精选层每个 Agent **只允许**分析传入的候选池，**禁止**自行扩大到全市场。

---

## 6. 市场可插拔（MarketRule，V1 即落地）

- A股、港股的一切差异（手数、涨跌停、T+0/T+1、费率、币种）**全部收敛在 `app/trading/market_rule.py`**。
- 撮合引擎、风控、费用计算**只依赖 `MarketRule` 接口**，严禁出现散落的 `if market == "A"`。
- 新增市场（如美股 V3）= 新增一个 `MarketRule` 实现，上层零改动。

```python
class MarketRule(Protocol):
    def normalize_qty(self, qty: int, symbol: str) -> int: ...
    def check_price_limit(self, symbol: str, price: float, prev_close: float) -> bool: ...
    def settlement_mode(self) -> Literal["T+0", "T+1"]: ...
    def calc_fees(self, side: str, price: float, qty: int) -> "Fees": ...
    def currency(self) -> str: ...

class AStockRule(MarketRule): ...   # T+1, ±10%(ST ±5%), 100股/手, 佣金万3, 印花千1(卖出)
class HKStockRule(MarketRule): ...  # T+0, 无涨跌停, 每股手数不同, HKD, 印花/交易征费/结算费
```

---

## 7. Signal 协议（AI ↔ 交易 的唯一通道）

- AI 引擎产出的所有交易意图，**必须**符合 `docs/contracts/signal.schema.json`。
- 交易引擎**只接受** Signal 作为输入，不直接读 Agent 内部对象。
- 任何一方修改 Signal 结构，**必须先改 schema 文件并经人工确认**，再改实现。
- AI 引擎**禁止** import `app/trading/*`；交易引擎**禁止** import `app/agents/*`。
- **`action` 枚举（5 值，同时覆盖选股推荐与持仓诊断）**：

| action | 含义 | 交易引擎映射 |
|--------|------|--------------|
| `BUY` | 新开仓（选股推荐） | 买单 |
| `ADD` | 加仓 | 买单 |
| `HOLD` | 保留 | 不下单 |
| `REDUCE` | 减仓 | 卖单（部分） |
| `SELL` | 清仓 / 抛出 | 卖单（全部） |

- 币种随市场：A→`CNY`，HK→`HKD`，必须与 `market` 一致；价格含 `target_price`/`stop_loss`/`take_profit`。

---

## 8. 目录结构与职责 + S 级目录锁

```
app/
├── core/        配置/安全/DB/Redis/日志/异常        [B级]
├── api/v1/      薄路由                              [B级]
├── schemas/     Pydantic + signals.py(Signal协议)   [A级]
├── models/      SQLAlchemy ORM                      [A级]
├── services/    业务逻辑                            [B级]
├── selection/   粗筛层(prescreen/factors)           [A级] V2接Qlib
├── agents/      LangGraph 4-Agent                   [A级]
├── trading/     撮合/MarketRule/风控/adapters       [S级] ⚠️资金红线
└── tasks/       Celery 任务                         [B级]
```

**S 级目录（`app/trading/`、含资金/订单/撮合/风控/费用/MarketRule）规则：**

1. **必须用最强模型实现**（见第 9 节），并经**人工逐行审查**后才能合并。
2. **本地区 Cursor 无法使用 Opus** → **S 级代码禁止在 Cursor 中实现**，必须在 **Claude Code（终端）+ Opus** 完成。
3. 任何 S 级改动**必须**附带：单元测试 + 边界测试 + 并发对账测试。
4. 当前激活模型若非 Opus，遇到 S 级文件**只输出设计与测试方案，不直接写实现**，并提示："⚠️ S 级路径，请切换至 Claude Code + Opus 4.8 再实现"。

---

## 9. 模型路由（人工执行，AI 负责提醒）

> 重要现实：本地区 **Cursor 不能用 Anthropic 模型**。因此 **Opus 主战场在 Claude Code 终端**（可在 Cursor 内置 Terminal 运行 `claude`）。

| 风险级 | 任务 | 工具 + 模型 |
|--------|------|-------------|
| S | 撮合 / MarketRule / 订单状态机 / Signal→Order / 风控 / 费用 | **Claude Code + Opus 4.8** + 人审 |
| A | LangGraph 编排 / 粗筛层 / OSS 集成 adapter / 大重构 | Claude Code + Opus |
| B | CRUD / 路由 / 定时任务 / 普通 API | Claude Code + Sonnet |
| C | uni-app 页面 / 图表 / 样式 / 补全 | Cursor + Composer/Codex/DeepSeek Flash |

- 本文件**不会自动切换模型**，由人工选择。AI 若发现"当前模型与任务风险级不匹配"，必须主动提示。
- **DeepSeek Flash 禁止用于任何会动钱的路径（S 级）。**

---

## 10. 命名规范

| 对象 | 规范 | 示例 |
|------|------|------|
| 文件名 | snake_case | `trade_service.py` |
| 类名 | PascalCase | `TradeService` |
| 函数/变量 | snake_case | `create_order` |
| 常量 | UPPER_SNAKE | `MAX_POSITION_PCT` |
| API 路径 | kebab-case | `/api/v1/daily-picks` |
| 数据库表/列 | snake_case | `trade_log` |

---

## 11. 数据库规范

- 主键统一 `UUID`（`gen_random_uuid()`）。
- 时间字段统一 `TIMESTAMPTZ`；金额字段统一 `DECIMAL(20,4)`。
- 每张表必须有 `created_at`，可变表加 `updated_at`。
- schema 隔离：`auth` / `trading` / `market` / `analysis`。
- 模拟账户与实盘账户**同表**，用 `account_type` 区分（`PAPER` / `LIVE`）。
- K 线用**声明式分区表**（按月），为 V2 迁 TimescaleDB 预留。
- 所有 schema 变更**必须**走 Alembic 迁移，禁止手改线上库。

---

## 12. 测试规范

- 框架：`pytest` + `pytest-asyncio`；DB 集成测试用 `testcontainers` 起临时 PG。
- 测试文件命名 `test_*.py`；目录镜像 `app/` 结构。
- **S 级强制**：撮合、费用、资产结算必须有**边界测试**（资金不足、超卖、涨跌停拒单、最小手数）和**并发对账测试**（高并发下账目不出现负数）。
- 覆盖率目标：核心模块（trading / selection / agents）> 80%。
- **测试先行**：S 级与 A 级代码，先写 test 再写实现。

---

## 13. AI Agent 规范（LangGraph）

- 每个 Agent **必须**输出**结构化 JSON**，字段与 schema 对齐，禁止自由文本当结果。
- 评分约定：技术面 / 基本面 0-100；舆情 -50~+50；投委会输出 `confidence` 0-100。
- Agent 间通过 LangGraph State 传递，**禁止**直接调用对方内部函数。
- 所有 LLM 调用必须有 `timeout` 和 `retry`，失败有降级（备用模型）。
- 投委会必须给出：`action`（5 值，见第 7 节）+ `confidence` + `reason_codes` + 自然语言 `reasoning`。
- Agent 只分析粗筛层给出的候选池（见第 5 节）。

---

## 14. 交易引擎规范（S 级）

- 模拟盘：**自研内存撮合**，不依赖第三方交易框架。
- 实盘（V2）：通过 `trading/adapters/base.py` 抽象接口接入，模拟与实盘**同一套** `place_order / cancel_order / get_positions / get_account`，切换只改配置。
- **风控阈值（统一，全项目以此为准）**：

| 规则 | 阈值 |
|------|------|
| 单票仓位上限 | ≤ 总资产 **15%** |
| 单行业集中度 | ≤ 30%（V1 可选，V2 强制） |
| 单日最大亏损熔断 | ≤ 5%（触发暂停 AI 托管下单） |
| AI 托管单笔确认 | 金额 > 配置阈值需二次确认 |

- 费用以 `MarketRule.calc_fees` 为准，**禁止**在撮合里硬编码费率。
- 所有下单 / 成交 / 撤单**必须**写完整审计日志（谁、何时、什么信号、什么结果）。

---

## 15. 安全与合规

- **禁止**硬编码密钥 / 密码 / API Key，一律走环境变量。
- 密码哈希用 `bcrypt`/`argon2`；鉴权用 JWT（access + refresh）。
- `IS_AUDIT_MODE=true` 时：买入/卖出/加仓/托管 → 关注/取消关注/AI 模拟实验；隐藏实盘入口。
- 每个含收益率的页面底部固定免责声明：「模拟收益仅供参考，不构成投资建议，入市有风险」。
- 仅"分析版"提交小程序审核；交易动作全部在 H5。
- 用户输入在边界层校验（Pydantic）；SQL 一律参数化（ORM），禁止字符串拼接。

---

## 16. 开源集成规范（Qlib / VeighNa，V2 启用）

> Qlib（全量，增强粗筛层）与 VeighNa（按需，主要实盘网关）是 **V2 既定集成项**，V1 已留好插槽（`selection/prescreen.py`、`trading/adapters/base.py`）。

集成时**必须**走 `docs/integrations/` 流水线，**严禁**整库喂给大模型：

1. **粗筛/侦察**：DeepSeek Flash 按 `FLASH-RECON-PROMPT.md` 定向读 ≤20 文件 → `*-RECON.md`。
2. **裁决/定契约**：Claude Code + Opus 按 `OPUS-ADAPTER-PROMPT.md` → `*-ADAPTER-DESIGN.md`。
3. **实现**：Sonnet 按 adapter 设计写薄封装，业务层**禁止** `import qlib` / `import vnpy`，只调 wrapper。
4. 单次集成会话**≤ 15 文件**；Opus 只用于 adapter 设计与交易/事件循环疑难。

---

## 17. Git 规范

- 分支：`main`(生产) / `dev`(开发) / `feat/xxx`(功能) / `fix/xxx`。
- 提交格式：`type(scope): message`，type ∈ {feat, fix, refactor, test, docs, chore}。
- **小步提交**：每次改动 ≤ 3-5 文件，测试通过即 commit。
- **禁止**：未经请求的 commit；提交 `.env`/密钥；`push --force` 到 main；跳过 hooks。
- S 级改动的 PR 描述必须注明"已用 Opus 实现 + 已人工审查"。

---

## 18. 环境变量（统一在 `core/config.py` 用 Pydantic Settings 管理）

| 变量 | 用途 |
|------|------|
| `IS_AUDIT_MODE` | 审核模式开关 |
| `DATABASE_URL` | PostgreSQL 连接 |
| `REDIS_URL` | Redis 连接 |
| `LLM_PRIMARY_API_KEY` / `LLM_BACKUP_API_KEY` | 主/备 LLM |
| `LLM_PRIMARY_MODEL` / `LLM_BACKUP_MODEL` | 模型名 |
| `AKSHARE_CACHE_TTL` | 行情缓存秒数 |
| `JWT_SECRET` / `JWT_EXPIRE_MINUTES` | 鉴权 |
| `MAX_POSITION_PCT` (默认 0.15) | 风控：单票上限 |
| `DAILY_LOSS_CIRCUIT_PCT` (默认 0.05) | 风控：熔断线 |

---

## 19. 协作机制（Cursor ↔ Claude Code）

- 二者**不共享聊天上下文**，只共享**同一仓库 + Git**。
- 短周期任务交接写 `docs/HANDOFF.md`（本轮完成 / 下轮待办 / 阻塞 / 目录归属）。
- **目录归属（减少并发冲突）**：

| 路径 | 主责 | 另一方 |
|------|------|--------|
| `app/trading/`、`app/agents/`、`app/selection/` | Claude Code | 仅可设计/Review，不直接写 |
| `frontend/` | Cursor | — |
| `app/api/`、`app/services/`（非 S 级） | Claude Code | Cursor 仅薄改 |
| `docs/contracts/` | 人工审批后双方只读 | — |

- 同一文件同一时刻只允许一方修改；契约先行（先改 schema/契约，再改实现）。

---

## 20. AI 行为红线（禁止事项）

1. **禁止**未经许可扩大改动范围（一个任务只做被要求的事）。
2. **禁止**删除/重建环境、删除数据库、批量删文件，除非明确授权。
3. **禁止**在 S 级路径用非 Opus 模型直接写实现。
4. **禁止**让 AI 引擎与交易引擎互相 import（只走 Signal）。
5. **禁止**在撮合/Agent 里硬编码费率、市场规则、密钥。
6. **禁止**整库喂 Qlib/VeighNa 给模型分析。
7. **禁止**生成与本文件技术栈不符的代码（如擅自引入 Kafka/Mongo）。
8. 不确定需求或边界时，**停下来问**，不要猜测后大改。

---

> 本文件不足之处会随开发逐步增补。任何 AI 在发现规则缺失或冲突时，应主动指出并建议补充，但**不得自行修改本文件**。
