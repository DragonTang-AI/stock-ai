# AI-Stock 终极架构定稿（V1 / V2 / V3）

> 作者：Cursor (Claude Opus 4.8) — 作为本项目未来主力开发者之一的定稿视角
> 日期：2026-06-01
> 定位：融合 5 份 AI 方案 + 两轮 Battle + Claude Final 版，补齐其缺口后的可落地三期蓝图
> 状态：**V1 可直接进场开发**；V2/V3 为演进路线，按真实数据与用户反馈触发

---

## 0. 这份文档与既有文档的关系

| 文档 | 定位 | 处置 |
|------|------|------|
| `AI-Stock架构.md` | 5 份 AI 原始方案 | 历史归档 |
| `AI-Stock架构终极Battle.md` | 第一轮裁判融合 | 历史归档 |
| `AI-Stock-Final-Architecture.md` | Claude Final（克制、A股向） | 被本文档**吸收并修订** |
| **本文档** | **唯一定稿（Source of Truth）** | **以此为准** |
| `docs/integrations/*.md` | Qlib/VeighNa 集成 prompt | **标记为 V2 资产**，V1 不启用 |

**本文档相对 Claude Final 的 3 处关键修订（我作为 Opus 的判断）：**

1. **补"轻量因子粗筛层"** —— 去掉 Qlib 后，仍需非 LLM 的海选，否则 LLM 无法面对全市场 5000+ 票。
2. **撮合引擎抽象 `MarketRule`** —— 对齐"V1 含 A股 + 港股"的真实需求（费率/手数/T+0·T+1/涨跌停各异）。
3. **模拟盘现实化** —— 不是"200 行"，规则正确性（T+1、涨跌停、最小手数、币种、并发对账）优先于滑点模拟。

---

## 1. 设计哲学（七条铁律，贯穿三期）

```
1. 够用即可        — 不引入还没遇到性能问题的组件（Kafka/Milvus/微服务都按需）
2. 纯 Python 主栈  — 降低 AI 编码认知负载，Cursor/Claude Code 对单语言效率最高
3. 信号驱动解耦    — AI 引擎与交易引擎只通过标准 Signal JSON 通信，互不 import
4. 模块化单体      — V1 单体按微服务边界分目录，V3 需要时"拎出即拆"
5. 市场可插拔      — A股/港股/美股通过 MarketRule + DataSource + Gateway 适配，上层不改
6. 资金即红线      — 涉及钱的代码全部 S 级：强模型 + 测试 + 人审 + 审计日志
7. 合规前置        — 审核模式、免责声明、产品分拆从 V1 第一行代码就在架构里
```

---

## 2. 三期总览（范围切分）

| 能力 | V1（核心闭环） | V2（智能增强 + 实盘） | V3（规模化 + 多市场） |
|------|----------------|------------------------|------------------------|
| 市场 | A股 + 港股（分析+模拟） | A股 + 港股（实盘） | + 美股 + 加密(可选) |
| 行情 AI 播报 | ✅ | ✅ 多模态/语音 TTS | ✅ 个性化 |
| 每日选股 Top5 | ✅ 因子粗筛 + 4-Agent | ✅ + Qlib 量化增强 | ✅ + 强化学习/在线学习 |
| 持仓诊断 + 置信分 | ✅ | ✅ + RAG 研报召回 | ✅ 组合级优化建议 |
| 模拟盘 手动 | ✅ | ✅ | ✅ |
| 模拟盘 AI 全托管 | ✅ | ✅ | ✅ |
| 实盘 手动跟单 | ⚠️ 仅提示/跳转 | ✅ Mini-QMT / 富途 | ✅ 多券商 |
| 实盘 AI 全托管 | ❌ | ✅（强风控+人审） | ✅ |
| 券商账户打通 | 占位 UI | ✅ OAuth + XtQuant | ✅ 多券商聚合 |
| 数据看板 | ✅ 日/周/月/年/回撤/夏普 | ✅ 归因分析 | ✅ 多账户/机构 |
| 用户分层 | 单一 | VIP | VIP/机构/基金经理 |
| 部署 | Docker Compose 单机 | Compose + 读写分离 | K8s + 微服务拆分 |
| 周期 | 10~12 周 | 8~12 周 | 按商业进度 |

---

## 3. V1 架构（详细 —— 现在就开发这套）

### 3.1 产品形态：必须 V1 就分拆（生死线）

```
┌──────────────────────────────────────────────────────────┐
│  产品 A：「AI 选股助手」(微信小程序, uni-app)              │
│   · 行情播报 / 选股推荐 / 持仓诊断(只读) / 数据看板        │
│   · 纯信息展示，无任何交易动作                            │
│   · 审核归类"工具/资讯"，文案用"分析/参考/观点"           │
│                                                          │
│  产品 B：「AI 投资实验室」(H5 Web App, uni-app H5 编译)    │
│   · 模拟交易(手动 + AI 托管) / 数据看板 / 实盘(V2)         │
│   · 独立域名，浏览器访问，不受应用商店金融审核约束        │
│   · 小程序内嵌 webview 或外链引流                        │
│                                                          │
│  共享：同一 FastAPI 后端 + 同一 AI 引擎                    │
│  开关：IS_AUDIT_MODE 控制功能可见性 + 文案降级            │
│  前端：uni-app 条件编译 #ifdef MP-WEIXIN / H5            │
└──────────────────────────────────────────────────────────┘
```

### 3.2 系统总览图

```
┌───────────────────────────────────────────────────────────────────────┐
│ Layer 1 · 客户端 (uni-app + Vue3 + Pinia + ECharts)                     │
│   小程序(分析版)            │            H5(交易版)                      │
│   行情播报·选股·诊断·看板    │   模拟交易(手动/托管)·看板·实盘(V2)         │
└───────────────────┬───────────────────────────┬───────────────────────┘
                    │   HTTPS / WebSocket / JWT   │
┌───────────────────▼───────────────────────────▼───────────────────────┐
│ Layer 2 · API & 业务服务层 (FastAPI, Python 3.12, 模块化单体)           │
│   api/  auth · market · analysis · portfolio · trade · simulation ·     │
│         dashboard · websocket                                          │
│   services/ (业务逻辑)   schemas/ (Pydantic + Signal协议)   core/        │
│   Celery + Redis(Stream)：每日选股 / 播报 / 日结清算 / 持仓诊断          │
│   WebSocket Manager：行情 / 订单回报 / AI 分析进度推送                   │
└────────┬──────────────────────────────────────────────┬───────────────┘
         │                                                │ Signal JSON
┌────────▼───────────────────────────┐   ┌───────────────▼───────────────┐
│ Layer 3 · AI 选股/分析引擎          │   │ Layer 4 · 交易执行引擎          │
│                                     │   │                                │
│ ① 粗筛层 (非 LLM, 纯 Python)        │   │ SimulationEngine (自研)        │
│    TA-Lib/pandas-ta 因子打分         │   │  ┌──────────────────────────┐ │
│    5000+ 票 → Top 30~50             │   │  │ MarketRule (可插拔)       │ │
│         │                           │   │  │  ├ AStockRule (T+1,±10%,  │ │
│         ▼                           │   │  │  │   100股,佣金万3+印花千1)│ │
│ ② LangGraph 4-Agent 投委会          │   │  │  └ HKStockRule (T+0,无涨跌│ │
│    技术面 / 基本面 / 舆情            │   │  │     停,每股手数异,HKD)     │ │
│         │                           │   │  └──────────────────────────┘ │
│         ▼                           │   │  内存撮合 + 滑点 + 费用 + 净值  │
│    投委会 Agent → 置信分0-100        │──▶│                                │
│    + Top5 + 播报文案                │Sig│ RealTradeAdapter (V2 占位接口)  │
│                                     │nal│  ├ MiniQmtAdapter (A股,XtQuant) │
│ LLM: Claude Sonnet(主)/DeepSeek(备) │   │  └ FutuAdapter   (港股,OpenAPI) │
└─────────────────────────────────────┘   └────────────────────────────────┘
         │                                                │
┌────────▼────────────────────────────────────────────────▼───────────────┐
│ 数据持久层                                                                │
│  PostgreSQL 16                                                           │
│   ├ auth schema      用户/认证                                          │
│   ├ trading schema   账户/订单/持仓/交易日志                            │
│   ├ market schema    K线/行情 (声明式分区表, 按月; V2→TimescaleDB)        │
│   ├ analysis schema  AI报告/播报 (JSONB)                                │
│   └ pgvector ext     向量列预留 (V2 RAG 启用)                           │
│  Redis 7                                                                │
│   行情热缓存 · 撮合队列(Stream) · WS会话 · Celery队列 · Session/限流     │
└──────────┬───────────────────────────────────────────────────────────────┘
           │
┌──────────▼───────────────────────────────────────────────────────────────┐
│ 外部数据源                                                                │
│  A股行情: AkShare(免费,首选) → Tushare Pro(付费,升级)                     │
│  港股行情: AkShare(基础) + 富途行情(可选)；V2 富途 OpenAPI 行情+交易一体   │
│  另类: 财经新闻 RSS / 雪球 → LLM 情绪打分                                 │
│  技术指标: TA-Lib / pandas-ta (本地计算, 不走 LLM)                        │
└───────────────────────────────────────────────────────────────────────────┘
```

### 3.3 关键决策（逐条）

**① 纯 Python 单栈，不要 NestJS 网关** —— FastAPI(Uvicorn) 足够扛 V1 并发；多一层 Node 只增加 AI 编码语言切换成本和部署复杂度。需要分流时加 Nginx 即可。

**② 选股 = 粗筛层 + 精选层（本文档对 Claude Final 的核心修订）**

```
全市场 5000+ 只
   │  ① 粗筛层（非 LLM，秒级，零 GPU，零 cn_data）
   │     · 动量/量价/估值/技术形态因子打分
   │     · pandas-ta 计算 + 加权排序
   ▼
Top 30~50（候选池）
   │  ② 4-Agent 精选（LLM，只看这 30~50 只 → 控成本）
   ▼
技术面Agent ─┐
基本面Agent ─┼─→ 投委会Agent → Top 5 + 置信分 + 理由 + 播报文案
舆情Agent   ─┘
```

> 这一层是 Claude Final 漏掉的：没有它，LLM 无法面对全市场，Token 成本和延迟都会失控。V2 接 Qlib 时，Qlib 替换/增强的正是这个"粗筛层"，上层 4-Agent 不动。

**③ 多 Agent 用 LangGraph，不用 AutoGen/CrewAI/Ruflo** —— 状态机清晰、文档完善、Claude Code 写起来最顺；V1 是工作流不是多轮对话，4 Agent + 投委会足够，不堆 Agent 数量。

**④ 模拟盘自研 + MarketRule 抽象（本文档第 2 处修订）**

```python
# schemas/signals.py —— 连接 AI 层与交易层的唯一协议
# 完整契约见 docs/contracts/signal.schema.json（以该文件为准）
@dataclass
class Signal:
    symbol: str            # "600519.SH" / "00700.HK"
    market: Literal["A", "HK"]      # 决定走哪套 MarketRule
    # action 5 值：BUY=新开仓 ADD=加仓 HOLD=保留 REDUCE=减仓 SELL=清仓/抛出
    # 交易引擎映射：BUY/ADD→买单, REDUCE/SELL→卖单(REDUCE部分,SELL全部), HOLD→不下单
    action: Literal["BUY", "ADD", "HOLD", "REDUCE", "SELL"]
    confidence: int        # 0-100
    currency: Literal["CNY", "HKD"]      # 与 market 一致：A→CNY, HK→HKD
    target_price: float | None
    stop_loss: float | None
    take_profit: float | None
    reason_codes: list[str]
    reasoning: str
    timestamp: datetime

# trading/market_rule.py —— 市场差异全部收敛在此
class MarketRule(Protocol):
    def normalize_qty(self, qty: int, symbol: str) -> int: ...   # 手数对齐
    def check_price_limit(self, symbol, price, prev_close) -> bool: ...
    def settlement_mode(self) -> Literal["T+0", "T+1"]: ...
    def calc_fees(self, side, price, qty) -> Fees: ...           # 佣金/印花/平台费
    def currency(self) -> str: ...

class AStockRule(MarketRule): ...   # T+1, ±10%(ST±5%), 100股, 佣金万3, 印花千1(卖)
class HKStockRule(MarketRule): ...  # T+0, 无涨跌停, 每股手数不同, HKD, 印花/交易征费/结算费
```

> 撮合主流程只依赖 `MarketRule` 接口，新增美股(V3)只加 `USStockRule`。**这是"低耦合、可扩展"的真正落点。**

**⑤ 数据库一库 + schema 隔离** —— PostgreSQL 16 一个实例，schema 逻辑隔离为 V3 拆分预留；K线用声明式分区表，V2 无缝迁 TimescaleDB（它是 PG 扩展非独立部署）；pgvector 列预留 V2 RAG。**不用** MongoDB/InfluxDB/Milvus/Kafka。

**⑥ 实时推送 WebSocket + Redis Stream，不用 Kafka** —— 日级选股 + 非高频，Redis 单节点 10w+ TPS 足够。

### 3.4 风控规则（V1 模拟盘即生效，写进 Signal 校验）

| 规则 | 阈值 | 说明 |
|------|------|------|
| 单票仓位上限 | ≤ 总资产 **15%** | 统一此值（消除 Final 文档 10%/20% 冲突） |
| 单行业集中度 | ≤ 30% | V1 可选，V2 强制 |
| 单日最大亏损熔断 | ≤ 5% | 触发暂停 AI 托管下单 |
| 止损 | 信号自带 stop_loss | 托管模式自动执行 |
| AI 托管单笔确认 | 金额 > 阈值需二次确认 | 防 AI 异常暴买 |

### 3.5 合规（V1 第一版就要有）

- 每个含收益率页面底部固定免责声明：「模拟收益仅供参考，不构成投资建议，入市有风险」
- `IS_AUDIT_MODE=true` 时：买入/卖出/加仓/托管 → 关注/取消关注/AI 模拟实验；隐藏实盘入口
- 小程序仅"分析版"提审；交易动作全部在 H5

---

## 4. V2 架构（智能增强 + 实盘，增量叠加）

> 触发条件：V1 跑通产品闭环、选股准确率经回测验证、有早期用户反馈。

### 4.1 增量能力

| 模块 | V2 做法 | 启用既有资产 |
|------|---------|--------------|
| **量化增强** | 接入 Qlib（Alpha158 + LightGBM）**替换/增强粗筛层**，4-Agent 不动 | `docs/integrations/*.md`（Flash侦察→Opus定adapter→`quant/qlib_runner.py`） |
| **A股实盘** | Mini-QMT (XtQuant) 本地终端，结构化 Signal → 下单；个人合规唯一解 | `trading/adapters/mini_qmt.py` |
| **港股实盘** | 富途 OpenAPI（FutuOpenD 网关），行情+交易一体 | `trading/adapters/futu.py` |
| **AI 全托管实盘** | 模拟同接口 + 强风控 + 人审 + 全审计；金额/频率限制 | 复用 SimulationEngine 接口 |
| **券商 OAuth** | 账户绑定、资金/持仓同步 | auth schema 扩展 |
| **时序优化** | K线分区表 → TimescaleDB hypertable | market schema 平滑迁移 |
| **RAG 增强** | pgvector 启用：研报/公告/新闻向量召回，喂给基本面/舆情 Agent | analysis schema + pgvector |
| **播报升级** | Edge-TTS 语音播报 | tasks/broadcast.py 扩展 |

### 4.2 V2 架构变化点

```
粗筛层：  pandas-ta 因子  ──升级──▶  Qlib(Alpha158+LightGBM) + 因子兜底
交易层：  仅模拟          ──新增──▶  RealTradeAdapter(Mini-QMT / 富途) [同 send_order 接口]
数据层：  PG 分区表       ──迁移──▶  TimescaleDB hypertable
          pgvector 预留   ──启用──▶  RAG 召回管道
风控：    模拟级          ──强化──▶  实盘级(资金校验/频率限制/熔断/人工确认)
```

> **关键：实盘与模拟用同一套 `place_order/cancel_order/get_positions/get_account` 接口，切换只改 Gateway 配置。** Qlib 与 vn.py 的集成严格走 `docs/integrations/` 流水线（Flash 侦察 → Opus 定 adapter → Sonnet 实现），避免整库喂给大模型。

---

## 5. V3 架构（规模化 + 多市场，按商业进度）

> 触发条件：用户量增长、需要团队协作、出现真实性能瓶颈。

### 5.1 增量能力

| 维度 | V3 做法 |
|------|---------|
| **美股** | 新增 `USStockRule` + 数据源(Yahoo/Polygon) + Gateway(IB/富途)，上层零改动 |
| **微服务拆分** | 按 schema 边界把 `analysis` / `trade` / `market` 从单体"拎出"为独立服务，gRPC/REST 通信 |
| **消息中台** | Redis Stream → **Kafka**（开盘/收盘尖峰削峰，多服务事件总线） |
| **容器编排** | Docker Compose → **Kubernetes**（弹性伸缩、滚动发布） |
| **数据库** | 读写分离、分库分表；行情走 TimescaleDB 集群；报告量大时评估文档库 |
| **向量库** | pgvector → **Milvus**（研报/新闻数据量大、RAG 召回精度要求高时） |
| **用户分层** | 普通/VIP/机构/基金经理；多账户管理、定制策略 |
| **数据飞轮** | 用户模拟/实盘行为 → 反馈数据集 → 微调选股模型/Agent prompt |
| **策略进化** | 引入强化学习/在线学习（FinRL 类）做策略层增强（研究性，谨慎上生产） |
| **可观测性** | Prometheus + Grafana + OpenTelemetry 全链路追踪 |

### 5.2 V3 拆分原则

```
单体模块化(V1) ── schema 边界即未来服务边界 ──▶ 微服务(V3)
   只在"团队 > 5 人 或 单服务成为瓶颈"时拆，不为微服务而微服务。
```

---

## 6. 技术栈清单（三期）

| 层级 | V1 | V2 增量 | V3 增量 |
|------|-----|---------|---------|
| 前端 | uni-app(Vue3+Vite) + Pinia + ECharts | TTS 播放 | — |
| 后端 | FastAPI 0.115+ + SQLAlchemy 2.0(async) | — | 微服务拆分 |
| 任务 | Celery + Redis | — | Kafka 事件总线 |
| Agent | LangGraph 0.3+ | RAG 管道 | 在线学习 |
| LLM | Claude Sonnet(主) + DeepSeek/GPT(备) | — | 自训/微调 |
| 量化 | TA-Lib / pandas-ta | **Qlib** | 强化学习 |
| 数据库 | PostgreSQL 16 + pgvector(列预留) | TimescaleDB + pgvector启用 | 读写分离/Milvus |
| 缓存/队列 | Redis 7 | — | Redis Cluster |
| 数据源 | AkShare → Tushare Pro | 富途 OpenAPI | Yahoo/Polygon |
| 实盘 | —(占位) | Mini-QMT(A) + 富途(HK) | IB(美股)/多券商 |
| 部署 | Docker Compose + Nginx | + 读写分离 | Kubernetes |
| CI/CD | GitHub Actions | — | + 蓝绿/金丝雀 |
| 监控 | 结构化日志 | Sentry | Prometheus+Grafana+OTel |

### 明确不做（及解禁条件）

| 技术 | V1 不用原因 | 解禁 |
|------|-------------|------|
| NestJS | 增加语言认知负载 | 基本永不（用 Nginx 替代分流） |
| Kafka | 运维成本 > 收益 | V3 用户/事件量大时 |
| Milvus | 无 RAG 场景 | V2 数据足够后（先 pgvector） |
| MongoDB | PG JSONB 覆盖 | 大概率永不 |
| Qlib | 初始化重、需 GPU | **V2 量化增强** |
| VeighNa | 模拟盘自研更轻 | **不用**（实盘直接 XtQuant/富途） |
| Ruflo | 太新不稳定 | 观察，仅用于开发期编排实验 |
| K8s | solo 不需要 | V3 团队/规模化 |
| 强化学习 | 工程化低、不可控 | V3 研究性，谨慎上生产 |

---

## 7. 项目目录结构（V1 蓝图，预留 V2/V3）

```
ai-stock/
├── CLAUDE.md                    # ⭐ 项目宪法（AI 操作手册）
├── .cursor/rules/               # Cursor 规则（按 glob 生效，含 S 级目录锁）
├── docker-compose.yml           # PG + Redis + API + Worker + Beat
├── pyproject.toml               # uv/poetry 依赖
├── alembic/                     # 数据库迁移
├── app/
│   ├── main.py                  # FastAPI 入口 + lifespan
│   ├── core/                    # config / security / database / redis / logging / exceptions
│   ├── api/v1/                  # 薄路由: auth / market / analysis / portfolio / trade / simulation / dashboard
│   │   └── websocket.py
│   ├── schemas/                 # Pydantic; signals.py = ⭐Signal协议
│   ├── models/                  # SQLAlchemy ORM: user/account/order/position/trade_log/report
│   ├── services/                # 业务逻辑层
│   ├── selection/               # ⭐ 选股
│   │   ├── prescreen.py         #   ① 粗筛层(因子打分, 非LLM)   [V2: 引入 qlib_runner]
│   │   └── factors.py
│   ├── agents/                  # ⭐ LangGraph 4-Agent
│   │   ├── orchestrator.py
│   │   ├── technical_agent.py / fundamental_agent.py / sentiment_agent.py
│   │   ├── committee_agent.py / broadcast_agent.py
│   │   └── tools/               # akshare_tools / ta_tools / news_tools
│   ├── trading/                 # ⭐ 交易引擎
│   │   ├── matching_engine.py   #   内存撮合
│   │   ├── market_rule.py       #   ⭐ AStockRule / HKStockRule  [V3: USStockRule]
│   │   ├── risk_control.py
│   │   └── adapters/            #   base.py [V2: mini_qmt.py / futu.py]
│   └── tasks/                   # Celery: daily_pick / broadcast / settlement / data_sync
├── tests/                       # pytest (交易/资金模块强制覆盖 + 并发对账)
├── scripts/                     # init_db / seed_data / backtest
├── frontend/                    # uni-app
│   └── src/ {pages, components(StockCard/KLineChart/ReturnChart/ConfidenceBadge), stores, api, utils}
├── docs/
│   ├── architecture/            # 本文档 + ADR
│   ├── contracts/               # signal.schema.json / api openapi
│   ├── integrations/            # Qlib/VeighNa 集成 prompt (标记 V2)
│   ├── design/                  # Ardot → Cursor 交接 (sitemap/tokens/screens)
│   └── HANDOFF.md               # Cursor ↔ Claude Code 任务交接
```

---

## 8. 数据库 Schema 草案（V1）

```sql
CREATE SCHEMA auth;      CREATE SCHEMA trading;
CREATE SCHEMA market;    CREATE SCHEMA analysis;
CREATE EXTENSION IF NOT EXISTS vector;   -- pgvector, V2 启用

-- 账户（模拟/实盘统一表, 用 account_type 区分）
CREATE TABLE trading.accounts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL,
    account_type  VARCHAR(10) NOT NULL,        -- 'PAPER' | 'LIVE'
    mode          VARCHAR(10) NOT NULL,        -- 'MANUAL' | 'AI_HOSTED'
    currency      VARCHAR(3)  NOT NULL DEFAULT 'CNY',
    initial_cash  DECIMAL(20,4) NOT NULL,
    cash          DECIMAL(20,4) NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 订单（状态机）
CREATE TABLE trading.orders (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id  UUID NOT NULL REFERENCES trading.accounts(id),
    symbol      VARCHAR(20) NOT NULL,
    market      VARCHAR(4)  NOT NULL,          -- 'A' | 'HK'
    side        VARCHAR(4)  NOT NULL,          -- 'BUY' | 'SELL'
    order_type  VARCHAR(8)  NOT NULL,          -- 'MARKET' | 'LIMIT'
    price       DECIMAL(12,4),
    qty         INTEGER NOT NULL,
    status      VARCHAR(12) NOT NULL,          -- PENDING|FILLED|PARTIAL|CANCELLED|REJECTED
    signal_id   UUID,                          -- 来源 AI 信号(可空=手动)
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- K线（声明式分区, V2→TimescaleDB）
CREATE TABLE market.kline_daily (
    symbol VARCHAR(20), trade_date DATE,
    open DECIMAL(12,4), high DECIMAL(12,4), low DECIMAL(12,4), close DECIMAL(12,4),
    volume BIGINT, amount DECIMAL(20,2),
    PRIMARY KEY (symbol, trade_date)
) PARTITION BY RANGE (trade_date);

-- AI 报告（JSONB, 含 4-Agent 完整输出）
CREATE TABLE analysis.daily_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_date DATE NOT NULL,
    report_type VARCHAR(20),                   -- STOCK_PICK|PORTFOLIO_DIAGNOSIS|BROADCAST
    content JSONB NOT NULL,
    -- embedding vector(1536),                 -- V2 RAG 启用
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 9. 全 AI 开发工作流（人机协同）

### 9.1 工具矩阵 + 模型路由（结合地区现实）

> **现实约束**：本地区 Cursor 无法使用 Anthropic 模型(Opus/Sonnet)。因此 **Opus 主战场放在 Claude Code（终端）**，Cursor 用区内可用模型。

```
你（产品/架构裁决/合规/资金人审）
│
├── Claude Code (终端, 在 Cursor 内置 Terminal 运行 `claude`)   —— 主力 ~65%
│     模型: Opus 4.8(S级/架构/Agent/交易/Review) / Sonnet(日常后端)
│     职责: 后端核心 · LangGraph Agent · 交易引擎 · 测试 · 集成 · 重构
│
├── Cursor (IDE)                                              —— 辅助 ~25%
│     模型: Composer / Codex / DeepSeek V4 Flash(区内可用)
│     职责: uni-app 前端 · ECharts · 联调 · 小改 · Tab 补全
│
├── Ardot (腾讯 AI 设计)                                       —— 设计 ~7%
│     职责: 6 核心屏出稿 → MCP 交付 Cursor → 改写 uni-app
│
└── 辅助: Research Agent(调研/合规) · UX Writer(文案) · QA Review(=Claude Code Opus 专审)
```

| 任务风险级 | 任务 | 模型/工具 |
|-----------|------|-----------|
| S（资金/交易/风控） | 撮合/MarketRule/订单状态机/Signal→Order | **Claude Code + Opus 4.8** + 人审 |
| A（架构/复杂） | LangGraph 编排/集成 adapter/大重构 | Claude Code + Opus |
| B（日常） | CRUD/路由/定时任务/普通 API | Claude Code + Sonnet |
| C（前端/机械） | uni-app 页面/图表/样式/补全 | Cursor + Composer/Codex/Flash |

### 9.2 协作总线（不是聊天互传，是 Git + 契约 + 交接单）

```
docs/contracts/signal.schema.json   ← 先定契约再写实现（前后端/AI-交易对齐）
CLAUDE.md / .cursor/rules           ← 长期约定 + S 级目录锁
docs/HANDOFF.md                     ← 短周期任务交接（本轮完成/下轮待办/阻塞/目录归属）
Git 分支                            ← 不同目录并行；同文件串行；小步 commit
```

### 9.3 黄金纪律

1. **CLAUDE.md 是宪法** —— 改它 = 修宪，需人工审批
2. **小步提交** —— 每次 ≤ 3-5 文件，测试通过即 commit
3. **测试先行** —— 资金代码必须边界测试 + 并发对账测试
4. **资金红线人审** —— 撮合/风控/MarketRule/费用 逐行审
5. **OSS 集成走流水线** —— 严禁整库喂模型；Flash 侦察 → Opus 定 adapter → Sonnet 实现
6. **日志即文档** —— 所有 API + Agent 思考 + 交易执行全审计

---

## 10. 开发节奏（V1：10~12 周）

| 阶段 | 周 | 内容 | 主力 |
|------|-----|------|------|
| P1 地基 | 1-2 | CLAUDE.md · FastAPI 骨架 · PG schema · Docker · JWT · pytest | Claude Code |
| P2 数据 | 3 | AkShare A股+港股接入 · 入库 · Celery 同步 · Redis 缓存 | Claude Code |
| P3 选股大脑 | 4-5 | **粗筛层** · LangGraph 4-Agent · 投委会 · 播报 · 每日任务 | Claude Code + Opus |
| P4 交易引擎 | 6-7 | **MarketRule(A/HK)** · 撮合 · 费用 · 账户 · AI托管/手动 · 日结 | Claude Code + Opus(人审) |
| P5 前端 | 8-9 | Ardot 出 6 屏 → Cursor uni-app · 看板 · WebSocket | Cursor + Ardot |
| P6 联调上线 | 10-12 | 全流程 · IS_AUDIT_MODE · 回测验证 · 部署 · 小程序提审 | Cursor + Claude Code |

> 注：含港股的 MarketRule 抽象使 P4 比纯 A 股多约 1 周，已计入。

---

## 11. 成本预算（V1 开发期，人民币）

| 项 | 标准版（推荐） |
|----|----------------|
| Claude（Opus 主力 + API 超额，跑在 Claude Code） | ¥6,000~11,000 |
| Cursor（区内模型，前端/日常） | ¥650~1,200 |
| Ardot（公测额度 + 加购） | ¥0~1,500 |
| 调研/文案 LLM | ¥400~500 |
| 云服务器(4C8G) + PG + Redis ×3月 | ¥1,500~3,000 |
| 数据源 + 域名 + 小程序认证 | ¥800~1,800 |
| **合计** | **¥1.5 万~2 万**（宽裕备 ¥2.5~3 万） |

运行时 LLM（内测期）：约 ¥500~3,000/月（看日活）。控成本关键：粗筛层挡掉海选、大盘播报全站一份缓存、持仓诊断按持仓数限流。

---

## 12. 风险登记册

| 风险 | 等级 | 缓解 |
|------|------|------|
| 小程序金融审核被拒 | 高 | 产品分拆 + IS_AUDIT_MODE + 仅分析版提审 |
| 港股规则被低估致返工 | 中高 | MarketRule 抽象 V1 即落地 |
| LLM 海选成本失控 | 中高 | 粗筛层先于 LLM；缓存；限流 |
| Cursor 无法用 Opus | 已知 | Opus 放 Claude Code；S 级禁在 Cursor 实现 |
| 资金逻辑静默错误 | 高 | Opus + 测试 + 人审 + 并发对账 |
| AI 托管异常暴买 | 高 | 单笔确认 + 频率限制 + 熔断 + 审计 |
| Qlib/vn.py 集成烧 Token | 中 | 走 docs/integrations 流水线，禁整库喂模型 |
| 实盘合规/资质 | 高 | V1 不上实盘；V2 Mini-QMT 合规路径 + 法务 |

---

## 13. 架构决策记录（ADR 摘要）

| # | 决策 | 理由 |
|---|------|------|
| 1 | 纯 Python 单栈，弃 NestJS | 降 AI 编码认知负载 |
| 2 | 选股 = 粗筛(非LLM) + 4-Agent(LLM) | 解决海选成本，本文档对 Final 的核心修订 |
| 3 | 模拟盘自研 + MarketRule 抽象 | 轻量 + 对齐 A股/港股双市场 |
| 4 | PostgreSQL 一库 + schema 隔离 | 够用、为 V3 拆分预留 |
| 5 | Redis Stream 弃 Kafka（V1） | 运维成本 > 收益 |
| 6 | LangGraph 弃 AutoGen/Ruflo | 稳定、Claude Code 友好 |
| 7 | Qlib/vn.py 推迟到 V2 | 初始化重；V1 先跑闭环 |
| 8 | Opus 放 Claude Code 而非 Cursor | 地区限制现实 |
| 9 | 产品分拆 + 审核模式 V1 落地 | 金融小程序生死线 |

---

## 14. 结语

这份定稿的核心不是"最先进"，而是**"最快跑通闭环、且每一步都为下一期留好接口"**：

- **V1** 用粗筛层 + 4-Agent + 自研撮合(双市场) 跑通"分析 + 模拟 + 看板"，10~12 周可内测；
- **V2** 在不动上层的前提下，把粗筛层换 Qlib、把 Gateway 接 Mini-QMT/富途、把 pgvector 启用 RAG；
- **V3** 沿 schema 边界拆微服务、加美股、上 Kafka/K8s，无需推倒重来。

**信号驱动解耦 + 市场可插拔 + 模块化单体**，是支撑这三期一脉相承的三根柱子。

准备好就告诉我，我可以接着产出 **`CLAUDE.md` + `.cursor/rules` + `docs/contracts/signal.schema.json`** 三件套，作为开发第一天的地基。
