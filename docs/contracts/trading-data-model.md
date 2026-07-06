# 交易数据模型契约（Account / Order / Trade / Position / EquitySnapshot）

> 状态：**V1 契约** ｜ 等级：**S 级（资金红线）** ｜ schema_version: **1.0**
> 定位：交易引擎与数据库的地基契约。所有涉及资金/订单/持仓的实现以本文件为准；与 `signal.schema.json` 配套。
> 修改本文件需人工审批。DB 落地于 PostgreSQL `trading` schema，变更走 Alembic。
> 关联：`AI-Stock-终极架构-Opus定稿.md`、`CLAUDE.md` 第 11/14 节、`docs/contracts/signal.schema.json`。

---

## 1. 设计原则（不可违背）

1. **账户按市场隔离**：一个账户只属于一个市场（A 或 HK），币种随之固定（CNY/HKD），**V1 不做跨币种混合账户与换汇**。用户可同时拥有多个账户，看板层做聚合展示。
2. **模拟与实盘同结构**：`PAPER` 与 `LIVE` 账户用同一套表，`account_type` 区分；实盘(V2)只换 Gateway，不改数据模型。
3. **金额精度统一** `DECIMAL(20,4)`；数量为整数股；币种字段显式存储。
4. **一切金额变动可追溯**：每笔成交 `Trade` 是资金/持仓变动的唯一来源，禁止直接改 `cash`/`position` 而无对应 Trade。
5. **不变量恒成立**：每次事务后账户级对账等式必须成立（见第 9 节），否则事务回滚。
6. **市场规则外置**：手数、涨跌停、T+0/T+1、费率全部来自 `MarketRule`，本契约不硬编码（费率示例仅作说明）。

---

## 2. 实体关系

```
User (auth schema)
  │ 1:N
Account (trading.accounts)        — PAPER/LIVE × MANUAL/AI_HOSTED，按市场隔离
  │ 1:N            │ 1:N                │ 1:N
Order            Position            EquitySnapshot
(trading.orders) (trading.positions) (trading.equity_snapshots)
  │ 1:N
Trade (trading.trades)            — 每笔成交一条，资金/持仓变动唯一来源
```

唯一约束：`Position` 在 `(account_id, symbol)` 上唯一；`EquitySnapshot` 在 `(account_id, snapshot_date)` 上唯一。

---

## 3. Account（账户）— `trading.accounts`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| user_id | UUID | FK→auth.users, NOT NULL | |
| account_type | VARCHAR(8) | NOT NULL | `PAPER` \| `LIVE`（V1 仅 PAPER 实际可交易） |
| mode | VARCHAR(10) | NOT NULL | `MANUAL` \| `AI_HOSTED` |
| market | VARCHAR(4) | NOT NULL | `A` \| `HK`（决定 MarketRule 与币种） |
| currency | VARCHAR(3) | NOT NULL | `CNY`(A) \| `HKD`(HK)，必须与 market 一致 |
| initial_cash | DECIMAL(20,4) | NOT NULL, >0 | 初始资金，默认 **1,000,000**（账户币种） |
| cash | DECIMAL(20,4) | NOT NULL, ≥0 | 可用现金 |
| frozen_cash | DECIMAL(20,4) | NOT NULL, ≥0, 默认 0 | 挂买单冻结的资金 |
| status | VARCHAR(10) | NOT NULL, 默认 ACTIVE | `ACTIVE` \| `SUSPENDED`(熔断) \| `CLOSED` |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

约束补充：
- 同一 `user_id` 下，`(account_type, mode, market)` 组合建议唯一（避免重复账户），可按产品需要放宽。
- `SUSPENDED`：触发单日熔断后置为此状态，暂停 AI 托管下单（手动可否操作由产品决定，默认也暂停）。

---

## 4. Position（持仓）— `trading.positions`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| account_id | UUID | FK, NOT NULL | |
| symbol | VARCHAR(20) | NOT NULL | 带后缀，如 600519.SH |
| market | VARCHAR(4) | NOT NULL | A \| HK |
| qty | INTEGER | NOT NULL, ≥0 | 总持仓股数 |
| available_qty | INTEGER | NOT NULL, ≥0, ≤qty | 可卖股数（A股 T+1：当日买入不计入，次日日结释放） |
| frozen_qty | INTEGER | NOT NULL, ≥0, ≤qty | 挂卖单冻结股数 |
| avg_cost | DECIMAL(20,4) | NOT NULL, ≥0 | 持仓均价（买入加权，含费用可选，V1 不含费用计入成本，费用单列） |
| last_price | DECIMAL(20,4) | NULL | 最新价（盯市用） |
| market_value | DECIMAL(20,4) | NOT NULL, 默认 0 | = qty × last_price |
| realized_pnl | DECIMAL(20,4) | NOT NULL, 默认 0 | 累计已实现盈亏（卖出结算） |
| unrealized_pnl | DECIMAL(20,4) | NOT NULL, 默认 0 | = (last_price − avg_cost) × qty |
| updated_at | TIMESTAMPTZ | NOT NULL | |

恒等关系：`available_qty + frozen_qty ≤ qty`（差额 = 当日 T+1 锁定部分）。`qty == 0` 时该行可保留(均价归零)或软删除，统一策略：**qty 归 0 保留行**，便于历史 realized_pnl 累计。

---

## 5. Order（订单）— `trading.orders`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| account_id | UUID | FK, NOT NULL | |
| symbol | VARCHAR(20) | NOT NULL | |
| market | VARCHAR(4) | NOT NULL | A \| HK |
| currency | VARCHAR(3) | NOT NULL | 与账户一致 |
| side | VARCHAR(4) | NOT NULL | `BUY` \| `SELL`（由 Signal.action 映射，见第 11 节） |
| order_type | VARCHAR(8) | NOT NULL | `MARKET` \| `LIMIT` |
| price | DECIMAL(20,4) | LIMIT 时 NOT NULL, >0 | 限价；市价单为 NULL |
| qty | INTEGER | NOT NULL, >0 | 委托数量（须经 MarketRule.normalize_qty 对齐手数） |
| filled_qty | INTEGER | NOT NULL, 默认 0, ≤qty | 已成交数量 |
| avg_fill_price | DECIMAL(20,4) | NULL | 成交均价 |
| status | VARCHAR(10) | NOT NULL | 见状态机第 5.1 |
| source | VARCHAR(10) | NOT NULL | `MANUAL` \| `AI_HOSTED` |
| signal_id | UUID | NULL | 来源信号（手动为 NULL） |
| reject_reason | VARCHAR(64) | NULL | 拒单原因码（见第 5.2） |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

### 5.1 订单状态机（合法转移，其余一律非法并拒绝）

```
            ┌──────────────────────────────────────────┐
            ▼                                          │
        [PENDING] ──fill_part──► [PARTIAL] ──fill_rest──► [FILLED]   (终态)
            │  │  │                  │  │
            │  │  └──cancel────────► [CANCELLED]                     (终态)
            │  │                     ▲
            │  └──reject──► [REJECTED] (终态)
            │
            └──收盘未成交/超时──► [EXPIRED] (终态)
                 [PARTIAL] 同样可 → CANCELLED / EXPIRED
```

| 当前 | 合法下一状态 |
|------|--------------|
| PENDING | PARTIAL, FILLED, CANCELLED, REJECTED, EXPIRED |
| PARTIAL | FILLED, CANCELLED, EXPIRED |
| FILLED / CANCELLED / REJECTED / EXPIRED | （终态，不可转移） |

- 终态订单**禁止**再修改 `filled_qty`/`status`。
- V1 自研撮合可选择「原子全成或拒绝」，但**状态机必须保留 PARTIAL**以兼容 V2 实盘部分成交。
- 任何非法转移必须抛出明确错误并写审计日志，**不得静默忽略**。

### 5.2 拒单原因码（`reject_reason`，机器可读）

`insufficient_cash`（资金不足）、`insufficient_position`（可卖不足）、`price_limit`（涨跌停限制）、`lot_size`（手数不合规）、`market_closed`（非交易时段）、`suspended`（停牌/账户熔断）、`signal_expired`（信号过期）、`risk_position_cap`（超单票上限）、`invalid_symbol`。

---

## 6. Trade（成交回报）— `trading.trades`

> 一个 Order 可对应多笔 Trade（部分成交）。Trade 是资金/持仓变动的**唯一合法来源**。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| order_id | UUID | FK, NOT NULL | |
| account_id | UUID | FK, NOT NULL | |
| symbol | VARCHAR(20) | NOT NULL | |
| market | VARCHAR(4) | NOT NULL | |
| side | VARCHAR(4) | NOT NULL | BUY \| SELL |
| price | DECIMAL(20,4) | NOT NULL, >0 | 成交价（含滑点） |
| qty | INTEGER | NOT NULL, >0 | 成交数量 |
| amount | DECIMAL(20,4) | NOT NULL | = price × qty（成交金额，不含费用） |
| commission | DECIMAL(20,4) | NOT NULL, ≥0 | 佣金 |
| stamp_tax | DECIMAL(20,4) | NOT NULL, ≥0 | 印花税（A股卖出 / 港股双向，按 MarketRule） |
| other_fees | DECIMAL(20,4) | NOT NULL, ≥0 | 过户费/平台费/交易征费/结算费等（按 MarketRule 汇总） |
| net_amount | DECIMAL(20,4) | NOT NULL | 实际现金变动：买入 = −(amount+费用)，卖出 = +(amount−费用) |
| realized_pnl | DECIMAL(20,4) | NOT NULL, 默认 0 | 本笔卖出实现盈亏（买入为 0） |
| traded_at | TIMESTAMPTZ | NOT NULL | |

费用来源：`commission/stamp_tax/other_fees` 全部由 `MarketRule.calc_fees(side, price, qty)` 计算，**禁止在 Trade 生成处硬编码费率**。

---

## 7. EquitySnapshot（净值快照）— `trading.equity_snapshots`

> 支撑数据看板的日/周/月/年收益率、回撤、夏普。每个账户每个交易日日结时落一条。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | |
| account_id | UUID | FK, NOT NULL | |
| snapshot_date | DATE | NOT NULL | 交易日；`(account_id, snapshot_date)` 唯一 |
| total_assets | DECIMAL(20,4) | NOT NULL | 净资产 = cash + frozen_cash + Σ position.market_value |
| cash | DECIMAL(20,4) | NOT NULL | 当日收盘可用现金 |
| position_value | DECIMAL(20,4) | NOT NULL | Σ 持仓市值 |
| daily_return | DECIMAL(12,8) | NOT NULL | 当日收益率（相对前一快照 total_assets） |
| cumulative_return | DECIMAL(12,8) | NOT NULL | 累计收益率（相对 initial_cash） |
| created_at | TIMESTAMPTZ | NOT NULL | |

> 看板的周/月/年收益、最大回撤(MDD)、夏普比率由 `EquitySnapshot` 时间序列计算，**不单独存储**（避免冗余口径不一致）。夏普所需无风险利率作为配置项。

---

## 8. 枚举汇总（与 DB / schema 对齐）

| 枚举 | 取值 |
|------|------|
| account_type | PAPER, LIVE |
| mode | MANUAL, AI_HOSTED |
| account.status | ACTIVE, SUSPENDED, CLOSED |
| market | A, HK（US 为 V3 预留） |
| currency | CNY, HKD |
| order.side | BUY, SELL |
| order_type | MARKET, LIMIT |
| order.status | PENDING, PARTIAL, FILLED, CANCELLED, REJECTED, EXPIRED |
| order.source | MANUAL, AI_HOSTED |
| reject_reason | insufficient_cash, insufficient_position, price_limit, lot_size, market_closed, suspended, signal_expired, risk_position_cap, invalid_symbol |

---

## 9. 不变量与对账规则（S 级核心，测试必须覆盖）

每次资金/持仓事务（下单冻结、成交、撤单解冻、日结）后，以下必须成立：

```
I1  cash ≥ 0  且  frozen_cash ≥ 0
I2  每个 Position: qty ≥ 0, available_qty ≥ 0, frozen_qty ≥ 0,
                  available_qty + frozen_qty ≤ qty
I3  资金守恒（账户级）：
      cash + frozen_cash
      == initial_cash + Σ(trades.net_amount)        ← 现金口径
I4  净资产对账：
      total_assets == cash + frozen_cash + Σ(position.qty × last_price)
I5  下买单冻结：frozen_cash 增加 = 预估金额(含预估费用)；成交/撤单后相应释放
I6  下卖单冻结：position.frozen_qty 增加 = 委托数量；成交/撤单后相应释放
I7  并发安全：同账户的资金/持仓更新必须串行化（行锁/乐观锁），
              高并发撮合下 I1~I4 不被破坏
```

> 任一不变量被破坏 ⇒ 事务回滚 + 告警日志。`tests/test_trading/` 必须包含针对 I1~I7 的边界与并发对账用例。

---

## 10. T+1 / T+0 处理（按 MarketRule.settlement_mode）

- **A 股 (T+1)**：买入成交后，`qty` 增加但 `available_qty` **不增加**；该批次在**次一交易日日结**时释放进 `available_qty`。卖出只能针对 `available_qty`。
- **港股 (T+0)**：买入成交后 `available_qty` **立即等于** `qty`（扣除 frozen_qty），当日可卖。
- 卖出校验：`委托卖出数量 ≤ available_qty − frozen_qty`，否则 `insufficient_position` 拒单。

---

## 11. Signal.action → Order.side 映射（与 signal.schema.json 一致）

| Signal.action | Order.side | 数量来源 |
|---------------|-----------|----------|
| BUY | BUY | 按 sizing/资金管理层计算（受单票 15% 上限约束） |
| ADD | BUY | 同上（在已有持仓上加） |
| HOLD | —（不生成订单） | — |
| REDUCE | SELL | 部分（按减仓比例 / sizing） |
| SELL | SELL | 全部可卖（清仓） |

下单前必经校验链：`信号有效期 → MarketRule.normalize_qty(手数) → check_price_limit(涨跌停) → 风控(单票≤15%/熔断) → 资金或持仓充足 → 冻结 → 入队撮合`。

---

## 12. 关键流程

### 12.1 下单 → 撮合 → 成交（写入顺序，保证可对账）
```
1. 校验链通过（第 11 节）
2. 创建 Order(status=PENDING) + 冻结资金/持仓 (I5/I6)
3. 撮合（SimulationEngine.match，依据 MarketRule 与当前行情+滑点）
4. 成交 ⇒ 写 Trade(net_amount, 费用, realized_pnl)
5. 原子更新：Account.cash/frozen_cash + Position(qty/available/avg_cost/realized) + Order(filled_qty/avg_fill_price/status)
6. 校验 I1~I4；不成立则整事务回滚
7. WebSocket 推送订单回报；写审计日志
```

### 12.2 日结（每日收盘 Celery 任务）
```
1. 拉收盘价 → 盯市更新 Position.last_price/market_value/unrealized_pnl
2. A股：释放 T+1 锁定 → available_qty = qty − frozen_qty
3. 计算并写 EquitySnapshot（total_assets/daily_return/cumulative_return）
4. 检查单日亏损是否触发熔断 → 必要时 Account.status=SUSPENDED
5. 撤销当日未成交 LIMIT 单 → status=EXPIRED，解冻
```

---

## 13. 与其它契约/规范的衔接

- 字段精度、UUID、TIMESTAMPTZ、schema 隔离 → 遵循 `CLAUDE.md` 第 11 节。
- 风控阈值（单票 15% / 单日熔断 5%） → `CLAUDE.md` 第 14 节，统一口径。
- 费用与市场规则 → `app/trading/market_rule.py`（A股/港股各一实现）。
- 实盘(V2)：`LIVE` 账户复用本模型，成交回报由 `trading/adapters/*` 回填，**表结构不变**。

---

## 14. 关键参数（已确认，2026-06-02）

1. **港股模拟账户初始资金**：**1,000,000 HKD**（与 A 股同数值不同币种，不做汇率折算）。
2. **熔断后交易**：`SUSPENDED` 时**手动与 AI 托管单均暂停**。
3. **新用户默认账户**：各市场各开一个 `PAPER/MANUAL`（A 股 CNY + 港股 HKD）；AI 托管账户由用户主动开通。
4. **持仓成本口径**：`avg_cost` **不计入买入费用**（费用单列，成本只用成交价加权）。
