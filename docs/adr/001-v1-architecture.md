# ADR 001 — V1 架构基线

## 状态

Accepted

## 日期

2026-06-30

## 背景

AI-Stock 是一个 A 股 + 港股 AI 选股 / 模拟交易平台。用户希望长期具备多智能体协作、云原生、实时处理、多模数据融合、低耦合、可扩展与可维护能力，但 V1 必须先快速跑通可用闭环。

第一轮架构 Battle 与后续 Opus 定稿已经明确：如果 V1 直接引入微服务、Kafka、Milvus、Qlib、VeighNa、Kubernetes 等重组件，会显著增加 solo / 小团队开发成本，并让 AI 协作更容易失控。

因此需要记录 V1 的架构基线，避免后续 Agent 在实现时反复推翻或扩张范围。

## 决策

V1 采用以下架构基线：

1. **产品分拆**：微信小程序只做分析版，H5 Web App 做模拟交易与后续实盘入口；通过 `IS_AUDIT_MODE` 控制审核模式。
2. **后端形态**：FastAPI 模块化单体，不拆微服务；按未来服务边界组织目录与数据库 schema。
3. **技术栈**：Python 3.12 + FastAPI + SQLAlchemy 2.0 async + Celery + PostgreSQL 16 + Redis 7 + LangGraph + uni-app(Vue3)；依赖管理用 uv。
4. **选股架构**：V1 选股 = 非 LLM 粗筛层 + 4-Agent 投委会；LLM 只分析候选池，不直接面对全市场。
5. **市场抽象**：A 股 / 港股差异全部收敛在 `MarketRule`；上层不得散落 `if market == ...`。
6. **AI ↔ 交易解耦**：AI 层与交易层只通过 `docs/contracts/signal.schema.json` 通信，禁止互相 import。
7. **交易核心 S 级**：`app/trading/` 涉及资金/订单/撮合/风控/费用，必须 Opus + 测试 + 人审；Cursor 内只设计不实现。
8. **数据层**：PostgreSQL 一库 + schema 隔离；Redis 做缓存/队列/WS/Session；V1 不引入 MongoDB、Milvus、Kafka。
9. **Qlib / VeighNa 定位**：V1 不启用；V2 作为既定集成项，通过 adapter 插槽接入，不推翻 V1 上层设计。
10. **协作机制**：使用 Git + worktree + 契约文件 + `docs/HANDOFF.md` 协作，不依赖聊天上下文共享。

## 备选方案

| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| V1 直接微服务 + Kafka + 多数据库 | 看起来更“云原生”，后期横向扩展便利 | 运维和联调成本高，solo/小团队会被基础设施拖慢 | 拒绝 |
| V1 直接集成 Qlib + VeighNa | 站在巨人肩膀上，长期有价值 | Qlib 初始化/训练重；VeighNa 模拟盘引入过重；会拖慢产品闭环 | 推迟到 V2，保留插槽 |
| V1 纯 LLM 全市场选股 | 实现快 | Token 成本和延迟不可控，且无法稳定分析 5000+ 票 | 拒绝 |
| V1 粗筛层 + 4-Agent | 成本可控，可解释，后续 Qlib 可替换粗筛层 | 粗筛初期不如 Qlib 成熟，需要自己定义因子 | 采纳 |

## 影响

### 正面影响

- V1 可以以较低工程复杂度跑通「分析 + 模拟盘 + 看板」闭环。
- Qlib / VeighNa 有明确 V2 插槽，后续接入不会推翻上层设计。
- `Signal` 和 `MarketRule` 让 AI 层、交易层、市场规则解耦。
- Git worktree 让多 Agent / 多工具并发时不互相踩文件。

### 负面影响 / 代价

- V1 的量化粗筛能力不如完整 Qlib，需要后续回测验证。
- 自研模拟撮合需要严格测试与人工审查，不能轻视资金逻辑。
- V1 暂不具备实盘能力，只能提供模拟盘与后续入口占位。

### 对后续阶段的影响

- V2：Qlib 替换或增强 `app/selection/prescreen.py`；实盘通过 `app/trading/adapters/` 接入 Mini-QMT / 富途 / VeighNa 网关能力。
- V3：按 schema 与目录边界拆出 market / analysis / trading 服务；需要真实规模或团队增长作为触发条件。

## 回滚 / 变更条件

只有满足以下条件之一，才重新评估本 ADR：

- V1 闭环已跑通，且粗筛层准确率或性能成为明确瓶颈。
- 用户规模或数据量证明 Redis / PostgreSQL 方案无法支撑。
- 团队规模超过 5 人，模块化单体开始明显阻碍并行开发。
- 券商实盘接入成为短期商业刚需，且已有合规资源支持。

## 关联文件

- `AI-Stock-终极架构-Opus定稿.md`
- `CLAUDE.md`
- `docs/contracts/signal.schema.json`
- `docs/contracts/trading-data-model.md`
- `docs/HANDOFF.md`
- `docs/WORKTREE.md`

