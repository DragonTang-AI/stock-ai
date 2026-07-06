# AI-Stock 智能选股交易平台 — 最终技术架构方案

> 作者视角：Claude Code (Opus 4.8) — 作为项目开发主力引擎
> 基于：5家AI方案融合 + 2026年技术现状 + AI Vibe Coding实战经验
> 日期：2026-06-01

---

## 一、核心设计哲学

**三条铁律：**
1. **够用即可，预留扩展** — 不引入你还没遇到性能问题的组件
2. **统一Python技术栈** — 一个人或小团队，语言切换的认知成本远大于性能收益
3. **信号解耦** — AI选股引擎和交易执行引擎之间通过标准JSON信号通信，互不依赖

**对各家方案的取舍：**

| 采纳 | 来源 | 理由 |
|------|------|------|
| 六层解耦架构理念 | Claude版 | 分层清晰，每层可独立演进 |
| 多Agent"投委会辩论"模式 | Gemini版 | 最贴近真实投资决策流程 |
| Python统一技术栈 | Loomy/Claude版 | solo/小团队最务实选择 |
| V1先做模拟盘 | 全员共识 | 实盘需券商资质，先跑通产品逻辑 |
| 产品分拆策略（分析版+交易版）| QClaw版 | 小程序审核的生死线问题 |
| 三层模型路由（Flash/Opus/Sonnet）| 项目已有 | 开发效率最大化 |

| 拒绝 | 来源 | 理由 |
|------|------|------|
| Kafka消息队列 | Claude版 | V1运维成本远高于收益，Redis Stream够用 |
| NestJS网关层 | 千问/Gemini版 | 增加语言切换负担，FastAPI本身够用 |
| 5+数据库混搭 | LongCat版 | 运维噩梦，PG+Redis足够 |
| V1直接上Qlib | QClaw版 | 数GB数据初始化繁琐，先用Agent+LLM选股 |
| Milvus向量库 | Claude/LongCat版 | V1无足够数据沉淀，V2再上RAG |
| Ruflo做Agent编排 | Gemini版 | 太新不稳定，LangGraph更成熟 |

---

## 二、系统架构总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    L1: 客户端层 (uni-app + Vue 3)                        │
│                                                                         │
│  产品A [分析版·小程序]        产品B [交易版·Web App/独立App]              │
│  · AI行情播报                 · 模拟交易（手动/AI托管）                    │
│  · 每日选股推荐卡片            · 实盘交易（V2）                           │
│  · 持仓诊断(只读)             · 完整数据看板                              │
│  · 数据看板(精简)             · 买卖日志                                  │
│                                                                         │
│  (两个产品共用同一套后端，通过功能开关 IS_AUDIT_MODE 区分)                  │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTPS / WebSocket / JWT
┌───────────────────────────────────▼─────────────────────────────────────┐
│                    L2: API网关 & 业务服务层 (FastAPI)                     │
│                                                                         │
│  · Nginx反向代理 + 限流                                                  │
│  · FastAPI统一入口（不拆微服务，用APIRouter做模块隔离）                     │
│  · 模块划分：                                                            │
│    ├─ auth/      用户认证 (JWT + 手机号/微信OAuth)                        │
│    ├─ market/    行情数据查询 + WebSocket实时推送                          │
│    ├─ analysis/  AI分析调度（选股/播报/持仓诊断）                          │
│    ├─ trade/     交易服务（模拟盘/实盘，统一接口不同实现）                   │
│    ├─ portfolio/ 持仓管理 + 数据看板                                      │
│    └─ report/    报告推送 + 播报生成                                      │
│  · Celery + Redis（异步任务：每日选股/播报生成/日结清算）                   │
│  · WebSocket Manager（实时行情/订单回报/AI状态推送）                       │
└──────┬──────────────────────────────────────────┬───────────────────────┘
       │                                          │
┌──────▼──────────────────────┐    ┌──────────────▼───────────────────────┐
│  L3: AI多智能体引擎          │    │  L4: 交易执行引擎                      │
│  (LangGraph编排)             │    │                                       │
│                              │    │  ┌─────────────────────────────┐     │
│  ┌────────────────────┐     │    │  │  模拟交易引擎                 │     │
│  │  Orchestrator      │     │    │  │  · 内存撮合 + 滑点模拟        │     │
│  │  (任务分发+结果汇聚) │     │    │  │  · Redis订单队列             │     │
│  └─────────┬──────────┘     │    │  │  · 手续费/印花税计算          │     │
│       ┌────┼────┐           │    │  │  · 日结清算                   │     │
│       ▼    ▼    ▼           │    │  └─────────────────────────────┘     │
│  ┌────┐┌────┐┌────┐        │    │                                       │
│  │技术││基本││舆情│        │    │  ┌─────────────────────────────┐     │
│  │面  ││面  ││面  │        │    │  │  实盘适配器 (V2)              │     │
│  │Agt ││Agt ││Agt │        │    │  │  · A股: Mini-QMT (XtQuant)   │     │
│  └──┬─┘└──┬─┘└──┬─┘        │    │  │  · 港股: 富途 OpenAPI        │     │
│     └──────┼─────┘          │    │  └─────────────────────────────┘     │
│       ┌────▼────┐           │    │                                       │
│       │投委会Agt│           │    │  信号接口: TradeSignal JSON            │
│       │(决策融合)│──────────────▶│  {symbol, side, qty, price,            │
│       │+置信分  │  Signal    │    │   confidence, source, timestamp}      │
│       └─────────┘           │    │                                       │
│                              │    │  统一接口：                            │
│  V2扩展：Qlib量化因子         │    │  place_order / cancel / get_positions │
│  Alpha158 → Top30初筛         │    │  get_account / get_equity_curve       │
│  → 再交给多Agent精选          │    │                                       │
└──────────────────────────────┘    └───────────────────────────────────────┘
       │                                          │
┌──────▼──────────────────────────────────────────▼───────────────────────┐
│                    L5: 数据持久层                                         │
│                                                                         │
│  PostgreSQL (主库)                                                        │
│  · 用户/账户/订单/持仓/交易日志                                            │
│  · AI分析报告 (JSONB字段)                                                 │
│  · 分区表存储K线数据 (V2可平滑迁移到TimescaleDB扩展)                        │
│  · pgvector扩展 (V2 RAG知识库预留)                                        │
│                                                                         │
│  Redis                                                                   │
│  · 实时行情缓存 (Hash)                                                    │
│  · 模拟撮合队列 (Stream)                                                  │
│  · WebSocket会话管理                                                      │
│  · Celery Broker + Result Backend                                        │
│  · 分布式锁 (防重复下单)                                                   │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────┐
│                    L6: 外部数据源 & 集成                                   │
│                                                                         │
│  行情数据:                                                                │
│  · A股: AKShare (免费兜底) + Tushare Pro (付费稳定)                        │
│  · 港股: 富途 OpenAPI / Yahoo Finance                                     │
│  · 新闻舆情: 财经RSS + 雪球/东财帖子爬取 → LLM情绪打分                     │
│                                                                         │
│  LLM服务:                                                                │
│  · 主力: Claude API (分析质量最高)                                         │
│  · 备选: 通义千问/GPT-4o (灾备/成本平衡)                                   │
│  · 播报TTS: 阿里云/讯飞语音合成                                            │
│                                                                         │
│  实盘接口 (V2):                                                           │
│  · A股: Mini-QMT (XtQuant) — 个人合规唯一解                               │
│  · 港股: 富途 OpenAPI — 需境外卡                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块详细设计

### 3.1 多智能体选股系统 (LangGraph)

```
用户请求 / 每日定时触发 (15:30收盘后)
       │
       ▼
┌──────────────────┐
│  Orchestrator    │ ── 获取当日全市场数据(AKShare)
│  (编排总线)       │ ── 按规则预筛：去ST/停牌/新股 → ~3000只
└────────┬─────────┘
    ┌────┼────┐
    ▼    ▼    ▼  (并行执行，各自独立)
┌────────────────┐
│ 技术面Agent    │  输入: K线+量价数据
│                │  分析: MACD/KDJ/布林带/RSI/成交量异动/K线形态
│                │  输出: {score: 0-100, signals: [...], reasoning: "..."}
├────────────────┤
│ 基本面Agent    │  输入: 财报数据+估值指标
│                │  分析: PE/PB/ROE/营收增速/负债率/现金流
│                │  输出: {score: 0-100, flags: [...], reasoning: "..."}
├────────────────┤
│ 舆情Agent      │  输入: 近3天新闻+社交媒体
│                │  分析: LLM情感打分/热点事件关联/政策影响
│                │  输出: {score: 0-100, sentiment: "...", events: [...]}
└────────┬───────┘
         │ 三份分析报告
         ▼
┌────────────────────┐
│  投委会Agent       │  接收三份报告 + 可选Qlib评分(V2)
│  (Judge/决策融合)   │  加权计算：技术40% + 基本30% + 舆情30%（可配置）
│                    │  输出:
│                    │  {
│                    │    top_picks: [{symbol, name, score, action, reasoning}...],
│                    │    confidence: 0-100,
│                    │    market_summary: "今日大盘...",
│                    │    broadcast_text: "各位投资者好..."
│                    │  }
└────────────────────┘
```

**V1选股策略**：3-Agent协作打分 → Top 5
**V2增强**：Qlib Alpha158因子模型先从5000只筛到Top30 → 再交给Agent精选 → Top 5

### 3.2 模拟交易引擎

```python
# 核心撮合逻辑（伪代码）
class SimulatedMatchingEngine:
    """基于Redis的内存撮合引擎"""
    
    async def submit_order(self, order: Order) -> OrderResult:
        # 1. 风控检查（资金充足、仓位限制、涨跌停价格校验）
        self.risk_check(order)
        
        # 2. 获取当前行情
        market_price = await self.redis.hget(f"quote:{order.symbol}", "last")
        
        # 3. 撮合逻辑
        if order.type == OrderType.MARKET:
            exec_price = market_price * (1 + random.uniform(-0.001, 0.001))  # 滑点
        elif order.type == OrderType.LIMIT:
            if not self.can_match(order, market_price):
                return self.pending(order)  # 挂单等待
            exec_price = order.price
        
        # 4. 计算费用（印花税+佣金+过户费）
        fees = self.calc_fees(order, exec_price)
        
        # 5. 更新持仓和资金
        await self.update_position(order, exec_price, fees)
        
        # 6. 推送订单回报
        await self.ws_broadcast(order.user_id, fill_event)
```

**两种模式：**
- **AI全托管**：Agent产生信号 → 自动下单 → 用户看数据看板
- **手动模式**：Agent给建议 → 用户确认 → 手动下单

### 3.3 数据看板指标体系

| 维度 | 指标 |
|------|------|
| 收益 | 日收益率、累计收益率、年化收益率、超额收益(vs沪深300) |
| 风险 | 最大回撤(MDD)、夏普比率、波动率、Calmar比率 |
| 交易 | 胜率、盈亏比、平均持仓天数、换手率 |
| AI | 选股命中率、置信分准确度回测、Agent一致性 |

### 3.4 持仓诊断与置信分数

```
用户持仓列表
    │
    ▼ (对每只持仓股票)
┌────────────────────┐
│ 持仓诊断Agent      │  输入: 持仓股当前K线+基本面+舆情+买入价+持仓天数
│                    │  
│  置信分计算:        │
│  · 0-30:  强烈建议减仓/清仓 (红色警告)
│  · 30-50: 建议减仓观望
│  · 50-70: 持有不动
│  · 70-85: 可适当加仓
│  · 85-100: 强烈建议加仓 (绿色信号)
│                    │
│  输出: {           │
│    action: "hold/sell/buy_more",
│    confidence: 72,
│    reasoning: "该股近期...",
│    risk_factors: [...],
│    target_price: 25.50,
│    stop_loss: 21.80
│  }                 │
└────────────────────┘
```

---

## 四、技术栈清单（V1确定版）

| 层级 | 技术选型 | 版本要求 |
|------|----------|----------|
| 前端框架 | uni-app + Vue 3 + Pinia | HBuilderX最新 |
| 图表库 | uCharts / ECharts (H5端) | — |
| 后端框架 | FastAPI + Uvicorn | Python 3.11+ |
| 异步任务 | Celery + Redis (Broker) | Celery 5.x |
| ORM | SQLAlchemy 2.0 (async) | — |
| 数据校验 | Pydantic v2 | — |
| Agent编排 | LangGraph | 最新稳定版 |
| LLM调用 | Claude API (langchain wrapper) | Claude 4 Sonnet |
| 数据库 | PostgreSQL 16 | + pgvector扩展 |
| 缓存/队列 | Redis 7 | Stream + Pub/Sub |
| 行情数据 | AKShare + Tushare Pro | — |
| 实盘(V2) | Mini-QMT (XtQuant) / 富途OpenAPI | — |
| 容器化 | Docker + Docker Compose | — |
| 反向代理 | Nginx | — |
| CI/CD | GitHub Actions | — |
| 监控 | Structlog + Sentry + Grafana(可选) | — |

---

## 五、项目目录结构

```
ai-stock/
├── CLAUDE.md                    # AI开发规范（命脉文件）
├── .cursorrules                 # Cursor IDE规则（同步CLAUDE.md）
├── docker-compose.yml           # 一键启动全部服务
├── Makefile                     # 常用命令快捷入口
│
├── backend/                     # Python后端（FastAPI单体，模块化隔离）
│   ├── main.py                  # FastAPI应用入口
│   ├── config/                  # 配置管理（环境变量、功能开关）
│   │   ├── settings.py
│   │   └── feature_flags.py    # IS_AUDIT_MODE等开关
│   ├── auth/                    # 认证模块
│   │   ├── router.py
│   │   ├── service.py
│   │   └── models.py
│   ├── market/                  # 行情模块
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── data_sources/       # AKShare/Tushare适配器
│   │   └── ws_manager.py       # WebSocket实时推送
│   ├── analysis/                # AI分析模块
│   │   ├── router.py
│   │   ├── agents/             # LangGraph多Agent
│   │   │   ├── orchestrator.py
│   │   │   ├── technical.py    # 技术面Agent
│   │   │   ├── fundamental.py  # 基本面Agent
│   │   │   ├── sentiment.py    # 舆情Agent
│   │   │   └── committee.py    # 投委会Agent
│   │   ├── stock_picker.py     # 每日选股调度
│   │   └── portfolio_advisor.py # 持仓诊断
│   ├── trade/                   # 交易模块
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── matching_engine.py  # 模拟撮合引擎
│   │   ├── risk_control.py     # 风控规则
│   │   └── adapters/           # 实盘适配器(V2)
│   │       ├── base.py         # 抽象接口 (Protocol)
│   │       ├── paper.py        # 模拟盘实现
│   │       ├── qmt.py          # Mini-QMT适配(V2)
│   │       └── futu.py         # 富途适配(V2)
│   ├── portfolio/               # 持仓管理模块
│   │   ├── router.py
│   │   ├── service.py
│   │   └── dashboard.py        # 数据看板计算
│   ├── report/                  # 报告生成模块
│   │   ├── router.py
│   │   ├── broadcast.py        # 每日播报生成
│   │   └── tts.py              # 语音合成
│   ├── common/                  # 公共组件
│   │   ├── database.py         # SQLAlchemy配置
│   │   ├── redis_client.py
│   │   ├── exceptions.py
│   │   └── logging.py          # Structlog配置
│   ├── models/                  # 数据库模型(全局)
│   │   ├── user.py
│   │   ├── account.py
│   │   ├── order.py
│   │   ├── position.py
│   │   └── report.py
│   ├── tasks/                   # Celery异步任务
│   │   ├── daily_pick.py       # 每日选股
│   │   ├── daily_broadcast.py  # 每日播报
│   │   ├── settlement.py       # 日结清算
│   │   └── data_sync.py        # 行情数据同步
│   └── tests/                   # 测试
│       ├── conftest.py
│       ├── test_auth/
│       ├── test_trade/
│       ├── test_analysis/
│       └── test_integration/
│
├── frontend/                    # uni-app前端
│   ├── src/
│   │   ├── pages/
│   │   │   ├── broadcast/      # AI播报页
│   │   │   ├── picks/          # 选股推荐页
│   │   │   ├── diagnosis/      # 持仓诊断页
│   │   │   ├── trade/          # 交易页(模拟/实盘)
│   │   │   ├── dashboard/      # 数据看板页
│   │   │   └── profile/        # 个人中心
│   │   ├── components/         # 公共组件
│   │   ├── stores/             # Pinia状态管理
│   │   ├── api/                # 接口封装
│   │   └── utils/
│   └── manifest.json
│
├── scripts/                     # 运维脚本
│   ├── init_db.py              # 数据库初始化
│   ├── seed_data.py            # 种子数据
│   └── backtest.py             # 历史回测验证
│
├── docs/                        # 项目文档
│   ├── api.md                  # API文档
│   ├── architecture.md         # 架构说明
│   └── integrations/           # 集成文档
│
└── deploy/                      # 部署配置
    ├── nginx/
    ├── docker/
    └── github-actions/
```

---

## 六、分期开发计划

### Phase 1（第1-2周）：基础骨架
- 项目初始化、Docker环境、数据库schema
- FastAPI框架搭建、模块目录、认证系统
- Redis配置、Celery配置
- CLAUDE.md + .cursorrules 规范文件
- **产出**：能跑起来的空壳服务 + 完整的开发规范

### Phase 2（第3-4周）：数据管道 + AI大脑
- AKShare行情数据接入（A股+港股）
- 行情数据存储（PG分区表）
- LangGraph 3-Agent搭建（技术面/基本面/舆情）
- 投委会Agent决策融合
- 每日选股Celery定时任务
- AI播报文案生成
- **产出**：每天能自动出选股报告和播报

### Phase 3（第5-6周）：模拟交易引擎
- 内存撮合引擎（市价单/限价单/滑点/费用）
- 模拟账户管理（初始资金/净值计算/回撤）
- AI全托管模式（Agent信号→自动下单）
- 手动模式（用户确认下单）
- 持仓诊断 + 置信分数
- 日结清算任务
- **产出**：完整可用的模拟投资系统

### Phase 4（第7-8周）：前端 + 数据看板
- uni-app骨架搭建
- AI播报页面（音频+文字）
- 选股推荐卡片（置信分+理由）
- 持仓诊断页面（红绿灯+建议）
- 模拟交易操作页面
- 数据看板（收益曲线/回撤/胜率/夏普）
- WebSocket实时推送集成
- **产出**：可以演示的完整产品

### Phase 5（第9-10周）：联调 + 上线
- 前后端联调
- IS_AUDIT_MODE审核模式实现
- 端到端测试（pytest + 并发测试）
- 性能优化
- Docker部署 + CI/CD
- 小程序提审（分析版）
- **产出**：可上线的MVP

### Phase 6（V2规划，第11周+）：
- Qlib量化因子集成（Alpha158 + LightGBM）
- Mini-QMT实盘接入
- 富途OpenAPI港股实盘
- TimescaleDB时序数据优化
- pgvector + RAG知识库
- 用户分层（普通/VIP/机构）

---

## 七、AI Vibe Coding 工作流分工

| 角色 | 工具 | 负责内容 |
|------|------|----------|
| 🧠 架构师 + 主力引擎 | **Claude Code (本工具)** | 后端核心、AI多Agent、数据库设计、Qlib/vnpy集成、测试、架构决策 |
| ⚡ 日常开发 | **Cursor** | 前端uni-app页面、局部修改、实时预览调试 |
| 🎨 UI原型 | **v0.dev** | 生成页面设计草稿，拷入Cursor精调 |
| 🔍 代码侦察 | **Flash模型(DeepSeek)** | 开源库源码分析(RECON阶段) |
| 📐 接口设计 | **Opus模型** | 适配器协议设计(ADAPTER-DESIGN阶段) |
| ✍️ 实现编码 | **Sonnet模型** | 按Opus设计实现具体adapter代码 |

**协作纪律：**
1. 每次改动不超过3-5个文件，改完测试+commit
2. 先写pytest再写业务代码（TDD）
3. 涉及资金路由的代码必须人工Review
4. CLAUDE.md是唯一的架构真理源，所有AI工具都读它
5. Git commit message说清改了什么，为什么改

---

## 八、关键风险与应对

| 风险 | 等级 | 应对措施 |
|------|------|----------|
| 小程序审核被拒（金融敏感词） | 🔴高 | IS_AUDIT_MODE开关；分析版不含任何交易功能；交易版走Web App |
| AI选股准确率不可控 | 🟡中 | 明确免责声明；提供历史回测数据；置信分透明化 |
| AKShare数据源不稳定 | 🟡中 | Tushare Pro作为备选；本地缓存3天数据；异常告警 |
| LLM API调用成本 | 🟡中 | 缓存相同查询结果；非实时分析用便宜模型；batch处理 |
| 模拟盘撮合精度 | 🟢低 | 模拟滑点+手续费+涨跌停限制；与真实数据对比校准 |
| 实盘券商接口申请周期长 | 🟡中 | V1全力做模拟盘验证产品逻辑；提前申请QMT权限 |

---

## 九、验证方案

1. **单元测试**：每个模块pytest覆盖率 > 80%
2. **集成测试**：testcontainers跑PG+Redis，验证完整交易流程
3. **回测验证**：用历史3个月数据跑选股策略，统计命中率
4. **并发测试**：模拟100用户同时下单，验证撮合正确性
5. **端到端**：前端调后端完整流程可跑通
6. **人工验收**：每个Phase结束产出可演示的功能

---

## 十、立即可执行的第一步

```bash
# 1. 初始化项目
mkdir -p ai-stock && cd ai-stock
git init

# 2. 创建项目骨架（由Claude Code执行）
# 包含：backend/, frontend/, docker-compose.yml, CLAUDE.md, Makefile

# 3. 启动开发环境
docker-compose up -d  # PostgreSQL + Redis

# 4. 跑通第一个API
uvicorn backend.main:app --reload

# 5. 第一个commit
git add . && git commit -m "feat: project scaffold with FastAPI + PG + Redis"
```

---

*本方案基于五家AI方案的最佳实践融合，以Claude Code作为主力开发引擎的视角设计，优先保证V1快速可用，同时为V2扩展预留清晰路径。*
