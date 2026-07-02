# AI-Stock 终极架构方案 (Claude Code 主力视角)

> 作者：Claude Code (Anthropic Claude Opus)
> 日期：2026-06-01
> 定位：结合5份AI方案的精华，从「实际编码落地」视角给出的最终决策版

---

## 一、我的核心判断：5份方案的元分析

### 各方案一句话定位

| 方案 | 核心优势 | 核心问题 |
|------|---------|---------|
| **Loomy版** | 综合裁判，取舍清晰 | 自身没有原创架构贡献 |
| **悟空版** | VeighNa+Qlib 双基座思路务实 | 缺乏多智能体设计，偏传统量化 |
| **Claude版** | 分层哲学最彻底，TimescaleDB选型精准 | Kafka/Milvus对V1过重 |
| **Gemini版** | 六层解耦+信号协议+审核模式，产品sense最强 | NestJS网关+Ruflo引入不必要复杂度 |
| **QClaw版** | 产品分拆策略(审核生死线)是所有方案的最大盲区补充 | 前端推荐Taro存争议 |

### 我的独到判断（其他5个AI都没说到的）

**1. V1不要上Qlib——这是我跟多数方案的最大分歧**

理由：
- Qlib的cn_data初始化需要下载数GB数据，经常因网络问题失败多次
- LightGBM训练A股全市场因子，CPU也能跑但慢，GPU环境配置又是一个坑
- V1的核心目标是**跑通产品闭环**，不是追求选股精度
- 3-Agent + LLM 直接基于AkShare数据做分析，已经能给出有价值的选股建议
- **V2再接Qlib做量化增强**，此时你已有用户反馈来验证方向是否正确

**2. 模拟交易引擎自研，不要依赖VeighNa**

理由：
- VeighNa是优秀的量化交易框架，但它的核心价值在**实盘Gateway**
- 模拟盘逻辑非常简单（内存撮合+滑点模拟+手续费计算），自己写200行Python就搞定
- 引入VeighNa做模拟盘 = 引入一个重量级依赖（安装复杂、版本冲突风险高）
- **V2接实盘时再引入Mini-QMT的XtQuant库**，轻量且合规

**3. 前端选uni-app不选Taro**

理由：
- uni-app的Vue3生态对AI编码更友好（Cursor/Claude Code对Vue的理解优于React/Taro）
- uni-app的小程序审核适配更成熟（条件编译、平台差异化处理）
- QClaw推荐的Taro虽然React生态更大，但在金融类小程序这个垂直领域，uni-app案例更多

**4. CLAUDE.md是这个项目成败的关键——不是锦上添花而是生死线**

作为Claude Code本身，我必须告诉你：
- 我每次执行任务时**首先读取CLAUDE.md**来理解项目规范
- 如果CLAUDE.md写得模糊，我的输出质量会显著下降
- 这个文件就是你给所有AI工具的「操作手册」，写得越具体，AI越不跑偏

---

## 二、最终技术架构（V1落地版）

### 架构哲学：四层解耦 + 信号驱动

```
设计原则：
1. 纯Python统一栈 — 降低认知负载，AI编码效率最高
2. 单体模块化 — 不是微服务，但目录结构按微服务边界划分
3. 信号驱动解耦 — AI引擎和交易引擎通过标准JSON信号通信
4. 够用即可 — 不引入还没遇到性能问题的组件
```

### 系统架构总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Layer 1: 客户端层                                      │
│                                                                         │
│  ┌─────────────────────┐    ┌──────────────────────────┐               │
│  │ 分析版 (小程序)      │    │ 交易版 (H5 Web App)       │               │
│  │ · 行情播报           │    │ · 模拟交易(手动/AI托管)    │               │
│  │ · 选股推荐           │    │ · 实盘交易(V2)            │               │
│  │ · 持仓诊断(只读)     │    │ · 数据看板                │               │
│  │ · 数据看板           │    │ · 完整功能               │               │
│  └─────────┬───────────┘    └──────────────┬───────────┘               │
│            │  uni-app (Vue3 + Pinia)        │                           │
│            │  IS_AUDIT_MODE 控制功能可见性    │                           │
└────────────┼────────────────────────────────┼───────────────────────────┘
             │ HTTPS / WebSocket / JWT         │
┌────────────┼────────────────────────────────┼───────────────────────────┐
│            ▼                                ▼                           │
│                    Layer 2: API & 业务服务层                              │
│                                                                         │
│  ┌────────────────── FastAPI (Python 3.12+) ──────────────────────┐    │
│  │                                                                 │    │
│  │  app/                                                           │    │
│  │  ├── api/           # APIRouter 按模块划分                       │    │
│  │  │   ├── auth/      # 用户注册/登录/JWT                          │    │
│  │  │   ├── market/    # 行情数据/实时推送                           │    │
│  │  │   ├── analysis/  # AI选股/持仓诊断/播报                        │    │
│  │  │   ├── trade/     # 模拟交易/实盘交易                           │    │
│  │  │   └── dashboard/ # 数据看板/收益统计                           │    │
│  │  ├── services/      # 业务逻辑层                                 │    │
│  │  ├── models/        # SQLAlchemy ORM                            │    │
│  │  ├── schemas/       # Pydantic 请求/响应模型                      │    │
│  │  ├── agents/        # AI多智能体 (LangGraph)                     │    │
│  │  ├── trading/       # 交易引擎 (模拟撮合/实盘适配器)               │    │
│  │  └── core/          # 配置/安全/日志/异常处理                      │    │
│  │                                                                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Celery + Redis (异步任务: 每日选股/播报生成/日结清算/持仓诊断)            │
│  WebSocket Manager (实时行情/订单回报/AI分析状态推送)                      │
└──────────┬──────────────────────────────────┬───────────────────────────┘
           │                                  │
┌──────────▼──────────────────┐  ┌────────────▼─────────────────────────┐
│  Layer 3: AI 多智能体引擎    │  │  Layer 4: 交易执行引擎                 │
│                             │  │                                       │
│  LangGraph Orchestrator     │  │  ┌─────────────────────────────┐     │
│  ┌────────────────────┐    │  │  │  SimulationEngine (自研)     │     │
│  │  任务分发器         │    │  │  │  · 内存撮合 (市价/限价)      │     │
│  │  (Orchestrator)    │    │  │  │  · 滑点模拟 (随机+固定)      │     │
│  └────────┬───────────┘    │  │  │  · 手续费/印花税计算         │     │
│           │                │  │  │  · 账户资产实时计算          │     │
│     ┌─────┼─────┐         │  │  └─────────────────────────────┘     │
│     ▼     ▼     ▼         │  │                                       │
│  ┌─────┐┌─────┐┌─────┐   │  │  ┌─────────────────────────────┐     │
│  │技术面││基本面││舆情 │   │  │  │  RealTradeAdapter (V2)      │     │
│  │Agent││Agent││Agent│   │  │  │  · A股: Mini-QMT (XtQuant)  │     │
│  └──┬──┘└──┬──┘└──┬──┘   │  │  │  · 港股: 富途 OpenAPI       │     │
│     │      │      │      │  │  │  · 风控: 单笔上限/日限/回撤  │     │
│     └──────┼──────┘      │  │  └─────────────────────────────┘     │
│            ▼              │  │                                       │
│  ┌────────────────────┐  │  │  ┌─────────────────────────────┐     │
│  │  投委会 Agent       │──┼──┼──▶│  标准信号 (Signal JSON)      │     │
│  │  · 加权融合         │  │  │  │  {action, symbol, price,    │     │
│  │  · 置信分 0-100     │  │  │  │   confidence, reason, ts}   │     │
│  │  · 播报文案生成     │  │  │  └─────────────────────────────┘     │
│  └────────────────────┘  │  │                                       │
└──────────────────────────┘  └───────────────────────────────────────┘
           │                                  │
┌──────────▼──────────────────────────────────▼───────────────────────────┐
│                    数据持久层                                              │
│                                                                         │
│  PostgreSQL 16                                                          │
│  ├── public schema: 用户/账户/订单/持仓/交易日志                           │
│  ├── market schema: K线/日线行情 (V1用分区表, V2考虑TimescaleDB)           │
│  ├── analysis schema: AI分析报告/播报记录 (JSONB)                         │
│  └── pgvector extension: AI对话历史向量 (V2 RAG用)                       │
│                                                                         │
│  Redis 7                                                                │
│  ├── 实时行情缓存 (Hash)                                                 │
│  ├── 模拟撮合队列 (Stream)                                               │
│  ├── WebSocket会话管理 (Set)                                             │
│  ├── Celery任务队列 (List)                                               │
│  └── 用户Session/限流 (String+TTL)                                       │
└─────────────────────────────────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────────────────┐
│                    外部数据源集成                                          │
│                                                                         │
│  行情数据:                                                               │
│  ├── A股: AkShare (免费, V1首选) → Tushare Pro (付费, V1+升级)            │
│  ├── 港股: 富途 OpenAPI (行情+交易一体)                                    │
│  └── 美股: Yahoo Finance (V2备用)                                        │
│                                                                         │
│  AI模型:                                                                 │
│  ├── 主力: Claude API (Sonnet 4 做Agent推理)                             │
│  ├── 备用: DeepSeek-V3 / GPT-4o (多模型灾备)                            │
│  └── 本地: 技术指标计算用 TA-Lib (不走LLM)                                │
│                                                                         │
│  实盘接口 (V2):                                                          │
│  ├── A股: Mini-QMT (XtQuant, 华泰/招商等券商)                            │
│  └── 港股: 富途 OpenAPI                                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 三、关键设计决策（逐条论证）

### 1. 为什么纯Python统一栈，不要NestJS网关？

| 维度 | FastAPI单栈 | NestJS网关+FastAPI |
|------|------------|-------------------|
| 开发认知成本 | 只需Python生态 | Python+Node.js两套 |
| AI编码效率 | Claude Code/Cursor只维护一种语言 | 切换语言时AI容易混淆风格 |
| V1并发需求 | FastAPI(Uvicorn) 单机 5000+ QPS | 实际用户<1万，5000QPS绰绰有余 |
| 未来扩展 | 加Nginx做反代+负载均衡 | NestJS本身也需要Nginx |
| 部署复杂度 | 1个Docker镜像 | 2个Docker镜像+内部通信 |

**结论**：V1阶段FastAPI完全够用。Gemini/千问推荐的NestJS是给百万用户准备的，solo开发者不需要。

### 2. 多智能体设计：4-Agent投委会模式

```
数据流向：

AkShare API ──▶ 技术面Agent ──▶ 技术评分JSON (0-100)
                                         │
AkShare API ──▶ 基本面Agent ──▶ 基本面评分JSON (0-100)  ──▶ 投委会Agent
                                         │                      │
新闻RSS/雪球 ──▶ 舆情Agent   ──▶ 情绪评分JSON (-50~+50) ──▶ │
                                                               ▼
                                                    最终决策JSON:
                                                    {
                                                      "symbol": "600519",
                                                      "action": "BUY",
                                                      "confidence": 82,
                                                      "target_price": 1850.00,
                                                      "stop_loss": 1720.00,
                                                      "reasoning": "...",
                                                      "agent_scores": {
                                                        "technical": 75,
                                                        "fundamental": 88,
                                                        "sentiment": 45
                                                      }
                                                    }
```

**为什么是LangGraph而非AutoGen/CrewAI/Ruflo？**

| 框架 | 优势 | 问题 |
|------|------|------|
| **LangGraph** | LangChain团队出品，文档完善，状态机模式清晰，Claude Code写起来最顺手 | 学习曲线略陡 |
| AutoGen | 微软出品，对话模式 | V1不需要多轮对话，更适合工作流模式 |
| CrewAI | 语法简洁 | 底层依赖不稳定，版本更新频繁break |
| Ruflo | 概念新颖 | 太新了，生态不成熟，文档不足，V1冒不起这个险 |

### 3. 模拟交易引擎：自研200行撮合

```python
# 核心数据结构
@dataclass
class Signal:
    """AI引擎输出的标准信号 — 连接AI层和交易层的唯一协议"""
    symbol: str          # 股票代码 e.g. "600519.SH"
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: int      # 0-100
    target_price: float
    stop_loss: float
    reasoning: str
    timestamp: datetime

@dataclass  
class Order:
    """交易订单"""
    order_id: str
    user_id: str
    symbol: str
    direction: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT"]
    price: float         # 限价单价格
    quantity: int
    status: Literal["PENDING", "FILLED", "CANCELLED"]

class SimulationEngine:
    """
    模拟撮合引擎 — 核心只有一个match方法
    V1自研，不依赖VeighNa，保持轻量
    """
    
    def match(self, order: Order, market_price: float) -> Optional[Trade]:
        # 1. 滑点模拟: 随机 ±0.1% (A股T+1场景足够)
        slippage = random.uniform(-0.001, 0.001)
        exec_price = market_price * (1 + slippage)
        
        # 2. 成交判定
        if order.order_type == "MARKET":
            return self._execute(order, exec_price)
        elif order.order_type == "LIMIT":
            if order.direction == "BUY" and exec_price <= order.price:
                return self._execute(order, exec_price)
            elif order.direction == "SELL" and exec_price >= order.price:
                return self._execute(order, exec_price)
        return None
    
    def _execute(self, order: Order, price: float) -> Trade:
        # 3. 费用计算 (A股)
        commission = price * order.quantity * 0.0003  # 万三佣金
        stamp_tax = price * order.quantity * 0.001 if order.direction == "SELL" else 0
        # 4. 更新持仓、资金、生成交易记录
        ...
```

### 4. 数据库策略：PostgreSQL一库搞定V1

```sql
-- V1: 所有数据一个PostgreSQL实例
-- 用schema逻辑隔离，为V2拆分做准备

CREATE SCHEMA auth;      -- 用户/认证
CREATE SCHEMA trading;   -- 账户/订单/持仓/交易日志  
CREATE SCHEMA market;    -- 行情/K线 (分区表按月)
CREATE SCHEMA analysis;  -- AI报告/播报 (JSONB)

-- K线存储: 用声明式分区表，V2无缝迁移到TimescaleDB
CREATE TABLE market.kline_daily (
    symbol      VARCHAR(20) NOT NULL,
    trade_date  DATE NOT NULL,
    open        DECIMAL(10,3),
    high        DECIMAL(10,3),
    low         DECIMAL(10,3),
    close       DECIMAL(10,3),
    volume      BIGINT,
    amount      DECIMAL(20,2),
    PRIMARY KEY (symbol, trade_date)
) PARTITION BY RANGE (trade_date);

-- AI分析报告: JSONB灵活存储
CREATE TABLE analysis.daily_reports (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_date DATE NOT NULL,
    report_type VARCHAR(20),  -- 'STOCK_PICK' | 'PORTFOLIO_DIAGNOSIS' | 'BROADCAST'
    content     JSONB NOT NULL,  -- 完整的Agent输出
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

**不用的数据库及原因**：
- ~~MongoDB~~: PG的JSONB完全覆盖非结构化需求，没必要多维护一套
- ~~InfluxDB~~: PG分区表存日K够用，V2再考虑TimescaleDB(它是PG扩展不是独立部署)
- ~~Milvus~~: V1没有RAG需求，pgvector做V2的向量检索足够
- ~~Kafka~~: Redis Stream对V1的消息量绰绰有余

### 5. 产品分拆策略（QClaw的最大贡献，必须V1就想清楚）

```
┌─────────────────────────────────────────────────────┐
│                  产品形态矩阵                         │
│                                                     │
│  产品A: "AI选股助手" (微信小程序)                     │
│  ├── 功能: 行情播报 + 选股推荐 + 持仓诊断(只读)       │
│  ├── 定位: 纯信息展示，无任何交易功能                  │
│  ├── 审核: 归类为"工具"类，避开金融审核                 │
│  └── 关键词: "分析""参考""观点" (避免"买入""加仓")      │
│                                                     │
│  产品B: "AI投资实验室" (H5 Web App)                   │
│  ├── 功能: 模拟交易(手动+AI托管) + 数据看板 + 实盘(V2) │
│  ├── 部署: 独立域名，浏览器直接访问                    │
│  ├── 优势: 不受应用商店审核限制                       │
│  └── 引流: 小程序内嵌webview跳转(审核通过率高)         │
│                                                     │
│  技术共享:                                           │
│  ├── 同一套FastAPI后端                               │
│  ├── 同一套AI多智能体引擎                             │
│  ├── IS_AUDIT_MODE 环境变量控制功能开关                │
│  └── 前端uni-app条件编译 #ifdef MP-WEIXIN             │
└─────────────────────────────────────────────────────┘
```

---

## 四、技术栈清单（最终决策版）

| 层级 | 技术选型 | 版本 | 选择理由 |
|------|---------|------|---------|
| **前端框架** | uni-app (Vue3 + Vite) | 3.x | 一码多端，AI编码友好 |
| **状态管理** | Pinia | 2.x | Vue3标配，TypeScript支持好 |
| **图表库** | ECharts (uni版) | 5.x | 金融图表最成熟 |
| **后端框架** | FastAPI | 0.115+ | 异步高性能，自动文档 |
| **ORM** | SQLAlchemy 2.0 | 2.x | async支持，类型安全 |
| **任务队列** | Celery + Redis | 5.x | 定时任务+异步处理 |
| **Agent框架** | LangGraph | 0.3+ | 状态机编排，可观测性强 |
| **LLM** | Claude API (Sonnet) | 最新 | 推理质量+代码理解 |
| **数据库** | PostgreSQL | 16 | 一库搞定所有 |
| **缓存/队列** | Redis | 7.x | 行情缓存+撮合队列+WS |
| **数据源(A股)** | AkShare | 最新 | 免费开源，V1首选 |
| **数据源(港股)** | 富途 OpenAPI | - | 行情+交易一体 |
| **技术指标** | TA-Lib / pandas-ta | - | 本地计算不走LLM |
| **容器化** | Docker + Compose | - | 一键启动全套环境 |
| **反代/HTTPS** | Nginx + Let's Encrypt | - | 生产部署标配 |
| **CI/CD** | GitHub Actions | - | 自动测试+部署 |

### 明确不用的技术（及原因）

| 技术 | 不用原因 | 什么时候上 |
|------|---------|-----------|
| NestJS/Node.js | V1并发不需要，增加认知负载 | 用户过50万再考虑 |
| Kafka | 运维成本过高，Redis Stream够用 | 用户过百万 |
| Milvus | 没有RAG场景 | V2有足够研报数据后 |
| MongoDB | PG JSONB覆盖需求 | 大概率永远不需要 |
| Qlib | 初始化复杂，V1用Agent选股 | V2量化增强 |
| VeighNa | 模拟盘自研更轻，实盘直接用XtQuant | V2实盘 |
| Ruflo | 太新不稳定 | 观察一年再说 |
| Kubernetes | solo开发不需要K8s | 团队>5人时 |

---

## 五、项目目录结构（开发蓝图）

```
ai-stock/
├── CLAUDE.md                    # ⭐ 项目规范文件（最重要）
├── .cursorrules                 # Cursor规则（与CLAUDE.md内容对齐）
├── docker-compose.yml           # 一键启动: PG + Redis + API + Worker
├── Dockerfile                   # Python后端镜像
├── pyproject.toml               # 依赖管理 (uv/poetry)
├── alembic/                     # 数据库迁移
│   ├── versions/
│   └── env.py
├── app/                         # ⭐ FastAPI 主应用
│   ├── __init__.py
│   ├── main.py                  # FastAPI入口 + lifespan
│   ├── core/                    # 核心配置
│   │   ├── config.py            # Pydantic Settings
│   │   ├── security.py          # JWT + 密码哈希
│   │   ├── database.py          # async SQLAlchemy engine
│   │   ├── redis.py             # Redis连接池
│   │   ├── logging.py           # 结构化日志 (JSON格式)
│   │   └── exceptions.py        # 全局异常处理
│   ├── api/                     # 路由层 (thin, 只做参数校验和调用service)
│   │   ├── v1/
│   │   │   ├── auth.py          # POST /register, /login, /refresh
│   │   │   ├── market.py        # GET /market/overview, /market/kline/{symbol}
│   │   │   ├── analysis.py      # GET /analysis/daily-picks, /analysis/broadcast
│   │   │   ├── portfolio.py     # GET/POST 持仓诊断
│   │   │   ├── trade.py         # POST /trade/order, GET /trade/history
│   │   │   ├── simulation.py    # 模拟盘专用路由
│   │   │   └── dashboard.py     # GET /dashboard/returns, /dashboard/metrics
│   │   └── websocket.py         # WS /ws/market, /ws/orders
│   ├── schemas/                 # Pydantic模型 (请求/响应)
│   │   ├── auth.py
│   │   ├── market.py
│   │   ├── trade.py
│   │   ├── analysis.py
│   │   └── signals.py           # ⭐ Signal标准协议定义
│   ├── models/                  # SQLAlchemy ORM模型
│   │   ├── user.py
│   │   ├── account.py           # 模拟账户 + 实盘账户
│   │   ├── order.py
│   │   ├── position.py
│   │   ├── trade_log.py
│   │   └── report.py
│   ├── services/                # 业务逻辑层
│   │   ├── auth_service.py
│   │   ├── market_service.py
│   │   ├── trade_service.py
│   │   ├── simulation_service.py
│   │   ├── portfolio_service.py
│   │   └── dashboard_service.py
│   ├── agents/                  # ⭐ AI多智能体
│   │   ├── orchestrator.py      # LangGraph主编排
│   │   ├── technical_agent.py   # 技术面分析
│   │   ├── fundamental_agent.py # 基本面分析
│   │   ├── sentiment_agent.py   # 舆情分析
│   │   ├── committee_agent.py   # 投委会决策
│   │   ├── broadcast_agent.py   # 播报文案生成
│   │   └── tools/               # Agent可调用的工具
│   │       ├── akshare_tools.py
│   │       ├── ta_tools.py      # 技术指标计算
│   │       └── news_tools.py    # 新闻抓取
│   ├── trading/                 # 交易引擎
│   │   ├── matching_engine.py   # 模拟撮合核心
│   │   ├── risk_control.py      # 风控规则
│   │   ├── fee_calculator.py    # 手续费计算
│   │   └── adapters/            # 实盘适配器(V2)
│   │       ├── base.py          # 抽象接口
│   │       ├── mini_qmt.py      # XtQuant适配
│   │       └── futu.py          # 富途OpenAPI适配
│   └── tasks/                   # Celery异步任务
│       ├── daily_pick.py        # 每日15:30选股
│       ├── broadcast.py         # 每日播报生成
│       ├── settlement.py        # 模拟盘日结
│       └── data_sync.py         # 行情数据同步
├── tests/                       # 测试
│   ├── conftest.py              # pytest fixtures
│   ├── test_agents/
│   ├── test_trading/
│   ├── test_api/
│   └── test_services/
├── scripts/                     # 运维脚本
│   ├── init_db.py               # 初始化数据库
│   ├── seed_data.py             # 导入历史行情
│   └── backtest.py              # 回测验证
├── frontend/                    # uni-app前端
│   ├── src/
│   │   ├── pages/
│   │   │   ├── index/           # 首页(行情播报)
│   │   │   ├── picks/           # 每日选股
│   │   │   ├── portfolio/       # 持仓诊断
│   │   │   ├── trade/           # 模拟交易
│   │   │   ├── dashboard/       # 数据看板
│   │   │   └── mine/            # 个人中心
│   │   ├── components/
│   │   │   ├── StockCard.vue    # 股票推荐卡片
│   │   │   ├── KLineChart.vue   # K线图组件
│   │   │   ├── ReturnChart.vue  # 收益曲线
│   │   │   └── ConfidenceBadge.vue  # 置信分徽章
│   │   ├── stores/              # Pinia状态
│   │   ├── api/                 # 后端API调用
│   │   └── utils/
│   ├── manifest.json
│   └── pages.json
└── docs/
    ├── api.md                   # API文档
    └── deployment.md            # 部署指南
```

---

## 六、开发节奏（10周落地计划）

### Phase 1: 地基搭建（第1-2周）

| 任务 | 工具 | 产出 |
|------|------|------|
| 写CLAUDE.md项目规范 | 人工+Claude Code | 项目宪法 |
| FastAPI项目骨架 | Claude Code | 可运行的空壳API |
| PostgreSQL schema设计 | Claude Code | Alembic迁移脚本 |
| Docker Compose | Claude Code | 一键启动环境 |
| JWT认证系统 | Claude Code | 注册/登录/刷新token |
| 基础pytest框架 | Claude Code | conftest + CI配置 |

**关键原则**：每个小模块写完+测试通过后立即Git Commit

### Phase 2: 数据管道（第3周）

| 任务 | 工具 | 产出 |
|------|------|------|
| AkShare数据接入脚本 | Claude Code | 日K/分钟K获取 |
| 行情数据入库 | Claude Code | 历史数据导入 |
| Celery定时同步 | Claude Code | 每日自动更新 |
| Redis实时行情缓存 | Claude Code | WebSocket推送 |

### Phase 3: AI多智能体大脑（第4-5周）⭐ 核心阶段

| 任务 | 工具 | 产出 |
|------|------|------|
| LangGraph编排搭建 | Claude Code | 4-Agent流程图 |
| 技术面Agent | Claude Code | MACD/RSI/布林带分析 |
| 基本面Agent | Claude Code | PE/PB/ROE/营收分析 |
| 舆情Agent | Claude Code | 新闻情感分析 |
| 投委会Agent | Claude Code | 加权决策+置信分 |
| 播报生成Agent | Claude Code | 自然语言文案 |
| 每日选股Celery任务 | Claude Code | 定时执行完整流程 |

**注意**：这是最复杂的阶段，需要反复调试prompt和Agent协作逻辑

### Phase 4: 模拟交易引擎（第6周）

| 任务 | 工具 | 产出 |
|------|------|------|
| 内存撮合引擎 | Claude Code | 市价/限价单 |
| 费用计算模块 | Claude Code | 佣金+印花税+过户费 |
| 模拟账户系统 | Claude Code | 初始资金+资产净值 |
| AI托管模式 | Claude Code | 自动接收信号下单 |
| 手动模式API | Claude Code | 前端下单接口 |
| 日结清算任务 | Claude Code | 每日收盘结算 |

### Phase 5: 前端开发（第7-8周）

| 任务 | 工具 | 产出 |
|------|------|------|
| uni-app项目初始化 | Cursor | 项目骨架 |
| 行情播报页 | Cursor + v0 | 首页UI |
| 选股推荐卡片 | Cursor | 每日Top5展示 |
| 持仓诊断页 | Cursor | 置信分+建议 |
| 模拟交易页 | Cursor | 下单+持仓 |
| 数据看板 | Cursor + ECharts | 收益曲线+指标 |
| WebSocket实时更新 | Cursor | 行情推送 |

### Phase 6: 联调上线（第9-10周）

| 任务 | 工具 | 产出 |
|------|------|------|
| 前后端联调 | Cursor + Claude Code | 全流程打通 |
| IS_AUDIT_MODE | Claude Code | 审核模式开关 |
| 历史回测验证 | Claude Code | 选股准确率评估 |
| 性能优化 | Claude Code | 接口响应<200ms |
| Docker部署到服务器 | Claude Code | 生产环境 |
| 小程序提审 | 人工 | 分析版上架 |

---

## 七、AI Vibe Coding 工作流规范

### 工具分工矩阵

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI 开发工具分工                                │
│                                                                 │
│  Claude Code (主力 70%)                                         │
│  ├── 后端全部代码 (FastAPI/SQLAlchemy/Celery)                    │
│  ├── AI多智能体引擎 (LangGraph Agent编写)                        │
│  ├── 交易引擎核心逻辑                                            │
│  ├── 测试代码 (pytest)                                           │
│  ├── Docker/部署脚本                                             │
│  ├── 数据库迁移                                                  │
│  └── 架构决策和重构                                              │
│                                                                 │
│  Cursor (辅助 25%)                                              │
│  ├── 前端uni-app页面开发                                         │
│  ├── ECharts图表组件                                             │
│  ├── 小范围bug修复                                               │
│  ├── CSS/样式调试                                                │
│  └── 前后端联调                                                  │
│                                                                 │
│  v0.dev (辅助 5%)                                               │
│  └── UI原型快速生成，拷入Cursor精调                               │
└─────────────────────────────────────────────────────────────────┘
```

### 黄金纪律（人机协同）

```
1. CLAUDE.md 是宪法
   - 每次开始新任务前，AI必须先读CLAUDE.md
   - 所有技术决策、命名规范、目录结构写入其中
   - 修改CLAUDE.md = 修宪，需要人工审批

2. 小步提交
   - 每次改动不超过3-5个文件
   - 改完立即跑pytest
   - 测试通过立即git commit
   - commit message格式: feat(module): 描述

3. 测试先行
   - 让AI先写test，再写实现
   - 涉及资金计算的代码，必须有边界测试
   - 并发场景必须有压力测试

4. 人工Review红线
   - 交易引擎的撮合逻辑 → 人工逐行审查
   - 风控规则 → 人工确认阈值
   - 资金计算 → 人工验算
   - LLM prompt → 人工评估输出质量

5. 日志即文档
   - 所有API请求必须有结构化日志
   - AI Agent的思考过程必须记录
   - 交易执行必须有完整audit trail
```

---

## 八、CLAUDE.md 模板（项目启动时第一个写的文件）

```markdown
# AI-Stock 项目规范

## 技术栈
- 后端: Python 3.12 + FastAPI + SQLAlchemy 2.0 + Celery
- 前端: uni-app (Vue3) + Pinia + ECharts
- 数据库: PostgreSQL 16 + Redis 7
- AI: LangGraph + Claude API
- 部署: Docker Compose + Nginx

## 架构规则
1. 分层: api → service → model，严禁跨层调用
2. 所有请求/响应必须用Pydantic schema定义
3. 数据库操作只能在service层，api层禁止直接操作DB
4. AI Agent只能通过标准Signal JSON与交易引擎通信
5. 第一版不拆微服务，用APIRouter做模块隔离

## 命名规范
- 文件名: snake_case (e.g. trade_service.py)
- 类名: PascalCase (e.g. TradeService)
- 函数: snake_case (e.g. create_order)
- 常量: UPPER_SNAKE (e.g. MAX_POSITION_SIZE)
- API路径: kebab-case (e.g. /api/v1/daily-picks)

## 数据库规范
- 主键统一用UUID
- 时间字段统一用timestamptz
- 金额字段用DECIMAL(20,4)
- 每个表必须有created_at, updated_at

## 测试规范
- 测试文件命名: test_xxx.py
- 使用pytest + pytest-asyncio
- 数据库测试用testcontainers
- 覆盖率目标: 核心模块>80%

## AI Agent规范
- 每个Agent必须输出标准JSON格式
- 投委会Agent必须给出confidence分数(0-100)
- Agent间通过LangGraph State传递数据
- 所有LLM调用必须有timeout和retry

## 交易引擎规范
- 模拟盘: 自研内存撮合，不依赖第三方库
- Signal协议: {symbol, action, confidence, target_price, stop_loss, reasoning, timestamp}
- 风控规则: 单笔不超过总资金20%，单日亏损不超过5%触发熔断
- 费用: 佣金万三(双向)，印花税千一(卖出)

## Git规范
- 分支: main(生产) / dev(开发) / feat/xxx(功能)
- 提交格式: type(scope): message
  - feat: 新功能
  - fix: 修复
  - refactor: 重构
  - test: 测试
  - docs: 文档

## 环境变量
- IS_AUDIT_MODE: 审核模式(隐藏交易功能)
- DATABASE_URL: PostgreSQL连接
- REDIS_URL: Redis连接
- CLAUDE_API_KEY: Claude API密钥
- AKSHARE_CACHE_TTL: 行情缓存时间(秒)
```

---

## 九、V2 演进路线图（备忘）

当V1跑通产品闭环后，根据用户反馈决定V2方向：

| 优先级 | V2功能 | 前置条件 |
|--------|--------|---------|
| P0 | 接入Qlib量化因子增强选股 | V1选股准确率验证完毕 |
| P0 | Mini-QMT实盘接入 | 去券商申请量化权限 |
| P1 | TimescaleDB迁移K线数据 | 数据量超过PG分区表性能瓶颈 |
| P1 | pgvector + RAG增强 | 积累足够研报/新闻数据 |
| P2 | 用户分层(VIP/机构) | 有付费用户需求 |
| P2 | Kafka替换Redis Stream | 用户量过百万 |
| P3 | 美股支持 | 核心功能稳定 |

---

## 十、总结：我作为Claude Code给你的终极建议

1. **不要追求"最先进"，追求"最快落地"** — 8周内跑出MVP比花3个月做完美架构重要100倍
2. **Python统一栈是你的最大杠杆** — 我(Claude Code)和Cursor处理Python的效率远高于多语言混合
3. **CLAUDE.md写透是你最好的投资** — 这是你给所有AI工具的操作手册，写1小时省100小时
4. **4-Agent投委会是AI选股的最优平衡** — 既不过于简单(单模型)，也不过度复杂(10+Agent)
5. **模拟盘自研是正确选择** — 200行Python比引入VeighNa的学习成本低10倍
6. **产品分拆必须V1就做** — 小程序审核是生死线，不是V2的事

**准备好了就告诉我，我来帮你写出第一版 CLAUDE.md 和项目骨架代码。**
