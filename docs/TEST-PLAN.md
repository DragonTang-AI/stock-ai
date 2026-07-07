# 集成测试计划 — AI-Stock V1

> **文档版本**：1.0  
> **创建日期**：2026-07-07  
> **对应任务**：T-M039  
> **测试范围**：全页面端到端联调，覆盖核心业务流 + 错误处理 + 边界条件  
> **后端依赖**：标注「🔗 需后端联调」的用例依赖后端接口/WebSocket/定时任务  

---

## 1. 页面清单与测试状态

| # | 页面路径 | 页面标题 | 核心功能 | 所属 Tab | 测试状态 |
|---|---------|---------|---------|---------|---------|
| 1 | `pages/login/index` | 登录 | JWT 登录/注册/Token管理 | - | ⬜ 待测 |
| 2 | `pages/market/index` | 行情 | 实时行情列表/搜索/K线查看 | 行情 | ⬜ 待测 |
| 3 | `pages/detail/index` | 行情详情 | K线图/技术指标/分时图 | 行情 → 详情 | ⬜ 待测 |
| 4 | `pages/selection/index` | 选股 | 委员会Top5/策略列表/一键选股 | 选股 | ⬜ 待测 |
| 5 | `pages/selection/detail` | 选股分析 | 单股4-Agent评分/操作建议 | 选股 → 详情 | ⬜ 待测 |
| 6 | `pages/selection/candidates` | 候选池 | 粗筛池分页/行业筛选/排序 | 选股 → 候选池 | ⬜ 待测 |
| 7 | `pages/portfolio/index` | 持仓 | 持仓列表/资产概览/分布饼图 | 持仓 | ⬜ 待测 |
| 8 | `pages/portfolio/analytics` | 持仓分析 | 资产曲线/统计指标/归因分析 | 持仓 → 分析 | ⬜ 待测 |
| 9 | `pages/portfolio/history` | 交易记录 | 成交记录/对账/交易历史 | 持仓 → 历史 | ⬜ 待测 |
| 10 | `pages/advisor/index` | AI 助手 | 对话交互/持仓诊断/选股建议 | AI助手 | ⬜ 待测 |
| 11 | `pages/hosted/index` | AI托管 | 托管开关/风控配置/信号日志 | - | ⬜ 待测 |
| 12 | `pages/dashboard/index` | 数据看板 | 收益率汇总/资产曲线/归因 | - | ⬜ 待测 |
| 13 | `pages/broadcast/index` | 每日播报 | 播报展示/TTS播放/历史播报 | - | ⬜ 待测 |
| 14 | `pages/watchlist/index` | 自选股 | 自选列表/添加/删除 | - | ⬜ 待测 |
| 15 | `pages/mine/index` | 我的 | 账户信息/快捷入口 | 我的 | ⬜ 待测 |
| 16 | `pages/mine/notifications` | 消息中心 | 通知列表/已读/清除 | 我的 → 通知 | ⬜ 待测 |
| 17 | `pages/mine/settings` | 设置 | 账户/交易/通知/关于/合规 | 我的 → 设置 | ⬜ 待测 |
| 18 | `pages/feedback/index` | 用户反馈 | 反馈提交 | - | ⬜ 待测 |

---

## 2. 核心流程集成测试

### 流程 1：用户登录 → 行情查看 → 选股 → 下单

> **业务路径**：用户从登录开始，浏览行情大盘，选择一只股票查看详情，通过选股委员会获得推荐，最终进入交易面板下单。

**前置条件**：
- 🔗 后端 Auth 服务运行，`POST /api/v1/auth/login` 可正常返回 JWT Token
- 🔗 行情数据就绪，`/api/v1/market/quote/{code}` 返回有效快照
- 🔗 选股委员会就绪，`/api/v1/selection/committee` 返回 Top5 推荐
- 🔗 交易引擎运行，`/api/v1/trading/account` 返回模拟账户
- 🔗 市场规则配置就绪，`/api/v1/trading/market-rule/{market}` 返回规则
- 前端 `pages/login/index` 页可正常加载

| 步骤 | 操作 | 预期结果 | 验证点 | 后端依赖 |
|------|------|---------|--------|---------|
| 1.1 | 打开小程序，未登录状态 | 自动跳转到登录页 `pages/login/index` | 路由守卫生效，TabBar 不可见 | - |
| 1.2 | 输入用户名/密码，点击登录 | 调用 `POST /auth/login`，成功后存储 Token，跳转行情页 | `accessToken` + `refreshToken` 写入 Storage；`useAuthStore.isLoggedIn` → `true` | 🔗 Auth |
| 1.3 | 行情页加载 | TabBar 显示 5 个 Tab；行情列表展示实时数据；下拉刷新可用 | `fetchQuote` 返回数据，列表项含涨跌幅颜色标识 | 🔗 Market |
| 1.4 | 点击某只股票 → 进入行情详情页 `pages/detail/index` | 展示 K 线图（含 MA/BOLL 等技术指标）、实时报价、涨跌幅 | `fetchKline` 返回 K 线数据；KlineChart 组件渲染正常 | 🔗 Market |
| 1.5 | 切换 K 线周期（日/周/月） | 图表重新加载对应周期数据 | `period` 参数正确传递；缓存 key 区分周期 | 🔗 Market |
| 1.6 | 点击「选股分析」→ 跳转选股详情 `pages/selection/detail` | 展示 4-Agent 评分卡片（技术/基本面/舆情/情绪） | `fetchStockDetail` 返回 `agents[]`，每项含 score/confidence/reasoning | 🔗 Selection |
| 1.7 | 返回选股首页 `pages/selection/index` | 展示委员会 Top5 推荐、策略列表 | `fetchCommitteeResults` 返回 Top5；`fetchStrategies` 返回策略列表 | 🔗 Selection |
| 1.8 | 对某只推荐股票点击「买入」→ 跳转持仓页并弹出 OrderPanel | OrderPanel 显示价格/手数输入框、费用预估、下单按钮 | `fetchTradingStockInfo` 返回实时价；`estimateFee` 预估费用 | 🔗 Trading |
| 1.9 | 输入手数、选择市价单 → 点击下单 → OrderConfirm 弹窗 | 展示二次确认（股票/方向/价格/费用）；免责声明可见 | `Disclaimer` 组件渲染；`OrderConfirm` 显示完整订单摘要 | - |
| 1.10 | 确认下单 | `POST /trading/order` 返回订单（status=PENDING）；成功后 Toast 提示 | 订单创建；`clearTradingCache` 被调用；持仓页自动刷新 | 🔗 Trading |

---

### 流程 2：AI 对话 → 持仓诊断

> **业务路径**：用户在 AI 助手页面发起对话，询问持仓情况，AI 返回诊断结果，用户查看持仓分析页验证。

**前置条件**：
- 🔗 AI 对话接口就绪（WebSocket SSE 或 REST `/api/v1/advisor/chat`）
- 🔗 持仓数据存在（至少 1 笔持仓）
- 用户已登录，`pages/advisor/index` 可正常加载

| 步骤 | 操作 | 预期结果 | 验证点 | 后端依赖 |
|------|------|---------|--------|---------|
| 2.1 | 点击 Tab「AI 助手」→ 进入 `pages/advisor/index` | 对话界面显示欢迎语；底部输入框可用 | 页面加载无报错；免责声明 `Disclaimer` 可见 | - |
| 2.2 | 输入「帮我诊断一下持仓」→ 发送 | 消息气泡发送成功；显示加载动画（三个点） | `LoadingSkeleton` 或打字动画显示 | 🔗 Advisor |
| 2.3 | 等待 AI 响应 | 返回持仓诊断卡片：含每只持仓股的风险评级、建议操作 | 诊断卡片格式化展示；含 `AuditBadge`（如审核模式开启） | 🔗 Advisor |
| 2.4 | 点击诊断卡片中的某只股票 → 跳转选股详情 | `pages/selection/detail` 展示该股的 4-Agent 评分 | 页面参数传递正确；`fetchStockDetail(symbol)` 被调用 | 🔗 Selection |
| 2.5 | 返回 AI 对话，输入「当前总收益率多少」 | AI 返回收益数据（总数/年化/夏普比） | 数据与 `pages/dashboard/index` 一致 | 🔗 Advisor + Analysis |
| 2.6 | 点击「查看完整持仓分析」链接 | 跳转 `pages/portfolio/analytics` | 资产曲线/统计指标正确渲染 | 🔗 Analysis |
| 2.7 | 验证统计指标与 AI 回答一致性 | 收益率/夏普/最大回撤数字匹配 | 前后数据源一致（同一接口） | - |

---

### 流程 3：AI 托管 → 信号执行 → 持仓更新

> **业务路径**：用户开启 AI 托管模式，系统自动接收信号并执行交易，持仓实时更新。

**前置条件**：
- 🔗 AI 托管后端运行，`/api/v1/hosted/status` 返回托管状态
- 🔗 信号生成系统运行，`/api/v1/hosted/signals` 返回信号列表
- 🔗 交易撮合引擎运行，信号可自动转为订单
- 用户有一个 PAPER 模拟账户（初始资金 1,000,000 CNY）

| 步骤 | 操作 | 预期结果 | 验证点 | 后端依赖 |
|------|------|---------|--------|---------|
| 3.1 | 进入 `pages/hosted/index` | 显示托管状态（默认 MANUAL）；风控参数配置表单可见 | `getHostedStatus()` 返回 is_active=false | 🔗 Hosted |
| 3.2 | 配置风控参数：风险等级=平衡、单票上限=15%、日止损=5% | 表单可编辑，保存后调用 `PATCH /hosted/config` | 请求体含 `risk_level/risk_position_cap/max_loss_daily` | 🔗 Hosted |
| 3.3 | 开启 AI 托管开关 → 弹窗确认 | 免责声明 + 「确认开启」按钮 | Disclaimer 组件；二次确认弹窗 | - |
| 3.4 | 确认开启 | `POST /hosted/switch` 返回 `mode=AI_HOSTED`；UI 显示「托管运行中」 | 开关状态更新；风控参数变为只读 | 🔗 Hosted |
| 3.5 | 等待信号生成 → 查看信号日志 | `getHostedSignals()` 返回信号列表；展示信号(action/symbol/confidence/status) | 信号卡片含信心度颜色标识 | 🔗 Hosted |
| 3.6 | 🔗 后端模拟信号执行（手动触发 `POST /hosted/trigger`） | 信号状态变为 EXECUTED/REJECTED；执行日志可查看 | `getHostedLogs()` 返回日志列表 | 🔗 Hosted + Trading |
| 3.7 | 查看执行日志详情 | 每条约含 action/symbol/price/qty/status/error | 成功：status=TRIGGERED；拒绝：status=BLOCKED+error 原因 | 🔗 Hosted |
| 3.8 | 跳转持仓页 `pages/portfolio/index` | 持仓列表出现新增股票（如有 BUY 信号执行成功） | 持仓数量/市值/浮盈正确更新 | 🔗 Trading |
| 3.9 | 返回托管页，关闭 AI 托管 | `POST /hosted/switch mode=MANUAL`；开关恢复关闭态 | 关闭后不会再生成新信号 | 🔗 Hosted |

---

### 流程 4：每日定时 → 播报生成 → 播放

> **业务路径**：系统定时生成每日播报，用户打开播报页查看文本和 TTS 音频。

**前置条件**：
- 🔗 播报生成定时任务已运行，`/api/v1/broadcast/today` 返回今日播报
- 🔗 TTS 音频已生成，`/api/v1/broadcast/audio/{id}` 返回音频 URL
- 前端 `components/selection/BroadcastPlayer.vue` 可用

| 步骤 | 操作 | 预期结果 | 验证点 | 后端依赖 |
|------|------|---------|--------|---------|
| 4.1 | 进入 `pages/broadcast/index` | 展示今日播报：概览文字、推荐列表（含信心度）、风险提示 | `fetchTodayBroadcast()` 返回 `Broadcast` 对象 | 🔗 Broadcast |
| 4.2 | 查看推荐列表 | 每只推荐股票显示 symbol/name/confidence/reason | 信心度高亮（>80% 绿色，50-80% 黄色，<50% 灰色） | - |
| 4.3 | 点击推荐股票 → 跳转选股详情 | `pages/selection/detail` 展示该股分析 | 导航传参正确 | 🔗 Selection |
| 4.4 | 点击「播放播报」按钮 | `BroadcastPlayer` 组件加载音频、显示播放进度 | `fetchBroadcastAudio(id)` 返回 `audio_url`；音频可播放/暂停 | 🔗 Broadcast |
| 4.5 | 暂停后恢复播放 | 从暂停位置继续 | `BroadcastPlayer` 状态管理正确 | - |
| 4.6 | 切换到历史播报列表 | 分页展示历史播报；`fetchBroadcastList()` 支持翻页 | `has_prev`/`has_next` 控制翻页按钮状态 | 🔗 Broadcast |
| 4.7 | 选择某一天的历史播报 | 展示该日播报详情（同理步骤 4.1-4.4） | `fetchBroadcastByDate(date)` 正常 | 🔗 Broadcast |
| 4.8 | 验证无播报日的展示 | 后端无该日数据 → 友好提示「暂无该日播报」 | `EmptyState` 组件渲染 | 🔗 Broadcast |

---

### 流程 5：数据看板 → 收益率查看

> **业务路径**：用户进入数据看板，查看投资组合收益率、资产曲线和归因分析。

**前置条件**：
- 🔗 日结任务已运行至少 30 个交易日（EquitySnapshot 有足够数据）
- 用户有持仓和交易历史
- `pages/dashboard/index` 可正常加载

| 步骤 | 操作 | 预期结果 | 验证点 | 后端依赖 |
|------|------|---------|--------|---------|
| 5.1 | 进入 `pages/dashboard/index` | 顶部展示概览卡片：总收益率、年化收益、跑赢基准、夏普比、最大回撤、胜率 | `fetchDashboardSummary()` 返回 6 个指标；`NumberRolling` 动画播放 | 🔗 Analysis |
| 5.2 | 查看资产曲线 | `LineChart` 展示 equity 曲线（含 benchmark 对比线） | `fetchEquityCurve(period)` 返回数据点；图表 X 轴日期、Y 轴净值 | 🔗 Analysis |
| 5.3 | 切换时间周期（日/周/月/年） | 曲线数据随周期变化，`NumberRolling` 数字更新 | 请求参数 `period` 正确传递；缓存 key 区分周期 | 🔗 Analysis |
| 5.4 | 查看归因分析 | `BarChart` 展示各因子贡献度（行业、风格、择时等） | `fetchAttribution(period)` 返回 `AttributionItem[]` | 🔗 Analysis |
| 5.5 | 查看统计指标详情 | `winRate`/`profitLossRatio`/`sharpeRatio`/`maxDrawdown` 单独展示 | `fetchStatistics()` 数据与概览卡片一致 | 🔗 Analysis |
| 5.6 | 在无持仓/无数据的场景下进入看板 | 友好提示「暂无数据，开始交易后将生成分析报告」 | `EmptyState` 组件处理空数据 | - |
| 5.7 | 对比看板数据与持仓页数据 | 总资产、收益率、盈亏数前后端一致 | 看板 `totalAssets` = 持仓页资产概览 `totalAssets` | 🔗 Analysis + Trading |

---

## 3. 跨流程验证与错误处理

### 3.1 Token 与认证

| 用例编号 | 场景 | 操作 | 预期结果 | 后端依赖 |
|---------|------|------|---------|---------|
| AUTH-01 | Token 过期 | 使用过期 Token 发起 API 请求 | 自动调用 `/auth/refresh` 刷新；刷新失败则跳转登录页 | 🔗 Auth |
| AUTH-02 | 手动退出登录 | 我的 → 设置 → 退出登录 → 确认 | `accessToken`/`refreshToken` 清除；跳转登录页 | - |
| AUTH-03 | 无 Token 访问受保护页 | 清除 Token 后尝试访问行情页 | 路由守卫拦截，跳转登录 | - |

### 3.2 错误码处理（request.ts 全局拦截器）

| 用例编号 | HTTP 状态码 | 触发方式 | 预期行为 |
|---------|------------|---------|---------|
| ERR-01 | 401 | 使用无效 Token 访问任何 API | 首次：尝试 refresh → 成功则重试；刷新仍 401 → 跳登录 |
| ERR-02 | 403（审核模式） | 后端返回 `error_code=AUDIT_MODE` | Modal 提示「当前处于审核模式，操作受限」 |
| ERR-03 | 403（权限不足） | 后端返回普通 403 | Toast 提示「暂无权限执行此操作」 |
| ERR-04 | 429（限流） | 短时间内大量请求 | Toast「请求频繁，稍后重试...」→ 指数退避重试（最多 2 次） |
| ERR-05 | 500 | 后端异常 | Toast「服务器异常，请稍后重试」→ 自动重试（最多 2 次） |
| ERR-06 | 网络断开 | 关闭网络后发起请求 | Toast「网络连接失败，请检查网络设置」→ 不自动重试 |
| ERR-07 | 网络恢复 | 断开网络后重新连接 | 请求恢复正常；`offline.ts` 状态更新 |

### 3.3 API 缓存验证

| 用例编号 | 场景 | 操作 | 预期结果 |
|---------|------|------|---------|
| CACHE-01 | 行情缓存 | 首次进入行情页 → 退出 → 30 秒内再次进入 | 30 秒内复用缓存（不发网络请求）；超时后重新拉取 |
| CACHE-02 | 选股缓存 | 查看选股 Top5 → 返回 → 5 分钟内再次查看 | 5 分钟内复用缓存 |
| CACHE-03 | K线缓存 | 查看某股日K → 切换周K → 切回日K | 日K 10 分钟内复用缓存；不同周期独立缓存 |
| CACHE-04 | 下单后缓存清除 | 下单成功后返回持仓页 | 持仓数据重新拉取（非缓存）；`clearTradingCache` 被调用 |
| CACHE-05 | 切换托管后缓存 | 开关 AI 托管 → 再次查看托管状态 | 缓存被清除，反映最新状态 |

### 3.4 合规组件验证

| 用例编号 | 场景 | 预期结果 |
|---------|------|---------|
| COMP-01 | 所有交易相关页面 | `Disclaimer` 组件可见（含「投资有风险，入市需谨慎」等文案） |
| COMP-02 | 审核模式开启 | `AuditBadge` 显示审核标识；敏感功能（下单/托管）隐藏或置灰 |
| COMP-03 | 选股详情页评分 | 明确标注「AI 分析仅供参考，不构成投资建议」 |

### 3.5 离线模式验证

| 用例编号 | 场景 | 预期结果 |
|---------|------|---------|
| OFFLINE-01 | 断网时查看行情列表 | 显示上次缓存数据 + 「当前离线」提示条 |
| OFFLINE-02 | 断网时发起下单 | 提示「网络不可用，请检查网络连接后重试」 |
| OFFLINE-03 | 网络恢复 | 提示条消失；数据自动刷新 |

### 3.6 空状态 / 无数据处理

| 用例编号 | 页面 | 场景 | 预期结果 |
|---------|------|------|---------|
| EMPTY-01 | 持仓页 | 无持仓 | `EmptyState` 显示「暂无持仓」引导文案 |
| EMPTY-02 | 选股页 | 委员会无推荐 | `EmptyState` 显示「暂无推荐结果」 |
| EMPTY-03 | 交易记录 | 无成交历史 | `EmptyState` 显示「暂无交易记录」 |
| EMPTY-04 | 数据看板 | 无快照数据 | `EmptyState` 显示「暂无数据，开始交易后将生成分析报告」 |
| EMPTY-05 | 候选池 | 筛选结果为空 | `EmptyState` 显示「未找到符合条件的股票」 |
| EMPTY-06 | 播报页 | 当日无播报 | `EmptyState` 显示「今日播报尚未生成」 |

### 3.7 移动端适配验证

| 用例编号 | 场景 | 预期结果 |
|---------|------|---------|
| MOB-01 | iPhone 14 Pro（刘海屏） | `safearea` 配置生效；顶部状态栏不被遮挡 |
| MOB-02 | Android 全面屏 | 底部导航不被虚拟按键遮挡 |
| MOB-03 | 键盘弹起时（下单/聊天） | 输入框自动上移，不被键盘遮挡 |
| MOB-04 | 横屏查看 K 线图 | K线图正常渲染；横竖屏切换不崩溃 |

---

## 4. 接口依赖矩阵

以下列出所有前端调用的后端 API 及对应的测试依赖。

| API Endpoint | Method | 前端调用位置 | 流程 | 依赖状态 |
|-------------|--------|-------------|------|---------|
| `/auth/login` | POST | `stores/auth.ts` → `request.ts` | 流程1 | 🔗 需后端联调 |
| `/auth/refresh` | POST | `request.ts` 拦截器 | ERR-01 | 🔗 需后端联调 |
| `/market/kline` | GET | `api/market.ts` → `KlineChart` | 流程1 | 🔗 需后端联调 |
| `/market/quote/{code}` | GET | `api/market.ts` → 行情列表 | 流程1 | 🔗 需后端联调 |
| `/selection/committee` | GET | `api/selection.ts` → 选股首页 | 流程1 | 🔗 需后端联调 |
| `/selection/stock/{symbol}` | GET | `api/selection.ts` → 选股详情 | 流程1/2 | 🔗 需后端联调 |
| `/selection/candidates` | GET | `api/selection.ts` → 候选池 | - | 🔗 需后端联调 |
| `/selection/strategies` | GET | `api/selection.ts` → 选股首页 | 流程1 | 🔗 需后端联调 |
| `/selection/industries` | GET | `api/selection.ts` → 候选池筛选 | - | 🔗 需后端联调 |
| `/trading/account` | GET | `api/trading.ts` → 持仓页 | 流程1/3 | 🔗 需后端联调 |
| `/trading/positions` | GET | `api/trading.ts` → 持仓页 | 流程1/3 | 🔗 需后端联调 |
| `/trading/order` | POST | `api/trading.ts` → OrderPanel | 流程1/3 | 🔗 需后端联调 |
| `/trading/estimate-fee` | POST | `api/trading.ts` → OrderPanel | 流程1 | 🔗 需后端联调 |
| `/trading/stock/{symbol}` | GET | `api/trading.ts` → OrderPanel | 流程1 | 🔗 需后端联调 |
| `/trading/market-rule/{market}` | GET | `api/trading.ts` → OrderPanel | 流程1 | 🔗 需后端联调 |
| `/hosted/status` | GET | `api/hosted.ts` → 托管页 | 流程3 | 🔗 需后端联调 |
| `/hosted/switch` | POST | `api/hosted.ts` → 托管开关 | 流程3 | 🔗 需后端联调 |
| `/hosted/config` | PATCH | `api/hosted.ts` → 风控配置 | 流程3 | 🔗 需后端联调 |
| `/hosted/logs` | GET | `api/hosted.ts` → 执行日志 | 流程3 | 🔗 需后端联调 |
| `/hosted/signals` | GET | `api/hosted.ts` → 信号日志 | 流程3 | 🔗 需后端联调 |
| `/hosted/trigger` | POST | `api/hosted.ts` → 调试触发 | 流程3 | 🔗 需后端联调 |
| `/broadcast/today` | GET | `api/broadcast.ts` → 播报页 | 流程4 | 🔗 需后端联调 |
| `/broadcast/list` | GET | `api/broadcast.ts` → 历史播报 | 流程4 | 🔗 需后端联调 |
| `/broadcast/{date}` | GET | `api/broadcast.ts` → 指定日播报 | 流程4 | 🔗 需后端联调 |
| `/broadcast/audio/{id}` | GET | `api/broadcast.ts` → TTS播放 | 流程4 | 🔗 需后端联调 |
| `/portfolio/summary` | GET | `api/analysis.ts` → 数据看板 | 流程5 | 🔗 需后端联调 |
| `/portfolio/statistics` | GET | `api/analysis.ts` → 统计指标 | 流程5 | 🔗 需后端联调 |
| `/portfolio/equity_curve` | GET | `api/analysis.ts` → 资产曲线 | 流程5 | 🔗 需后端联调 |
| `/portfolio/attribution` | GET | `api/analysis.ts` → 归因分析 | 流程5 | 🔗 需后端联调 |
| `/portfolio/overview` | GET | `api/analysis.ts` → 资产概览 | 流程2/5 | 🔗 需后端联调 |
| `/portfolio/distribution` | GET | `api/analysis.ts` → 持仓分布 | - | 🔗 需后端联调 |
| `/watchlist/add` | POST | `api/selection.ts` → 自选添加 | - | 🔗 需后端联调 |
| `/watchlist/remove` | POST | `api/selection.ts` → 自选移除 | - | 🔗 需后端联调 |

---

## 5. 组件与工具模块功能验证

| 模块 | 验证点 | 相关用例 |
|------|--------|---------|
| `KlineChart.vue` | K线渲染、MA/BOLL 指标、周期切换、横竖屏自适应 | 流程1 |
| `LineChart.vue` | 资产曲线、多系列、主题切换、tooltip | 流程5 |
| `BarChart.vue` | 归因分析柱状图、标签显示 | 流程5 |
| `PieChart.vue` | 持仓分布饼图、图例 | 持仓页 |
| `OrderPanel.vue` | 价格/手数输入、MarketRule 校验、费用预估 | 流程1 |
| `OrderConfirm.vue` | 二次确认弹窗、订单摘要、免责声明 | 流程1 |
| `BroadcastPlayer.vue` | 音频加载、播放/暂停、进度条 | 流程4 |
| `Disclaimer.vue` | 交易相关页面免责声明文案 | COMP-01 |
| `AuditBadge.vue` | 审核模式标识 | COMP-02 |
| `NumberRolling.vue` | 收益率数字滚动动画 | 流程5 |
| `LoadingSkeleton.vue` | 骨架屏加载态 | 各页面加载 |
| `EmptyState.vue` | 空数据友好提示 | EMPTY-01~06 |
| `VirtualList.vue` | 长列表虚拟滚动性能 | 行情列表/候选池 |
| `NotificationCenter.vue` | 通知列表/已读/清除 | 消息页 |
| `ErrorPage.vue` | 页面级错误兜底 | 全局 |
| `LazyImage.vue` | 图片懒加载 | 各页面 |
| `ConfirmDialog.vue` | 通用确认弹窗 | 退出/删除/关闭托管 |
| `SkeletonScreen.vue` | 全屏骨架屏 | 首次加载 |

---

## 6. 测试环境要求

| 项目 | 要求 |
|------|------|
| 前端运行环境 | uni-app H5 + 微信小程序（iOS/Android 真机或模拟器） |
| 后端环境 | FastAPI 服务全量运行（Auth + Market + Trading + Hosted + Broadcast + Selection + Advisor） |
| 数据库 | PostgreSQL（含 `trading` schema 完整表结构） |
| 初始数据 | 至少 1 个模拟账户（PAPER/MANUAL，初始资金 1,000,000 CNY）；至少 30 个交易日的 EquitySnapshot 数据 |
| 行情数据 | 至少 5 只 A 股的实时行情 + K 线数据（含 MA/BOLL 指标） |
| 选股数据 | 至少 3 条委员会推荐结果；候选池 20+ 股票 |
| 播报数据 | 至少 1 条今日播报（含 TTS 音频 URL） |
| AI 托管 | 托管服务运行中，信号生成器已配置 |

---

## 7. 测试执行检查清单

### 7.1 执行前检查

- [ ] 后端所有服务已启动并通过健康检查
- [ ] 数据库已迁移到最新版本（Alembic head）
- [ ] 测试账户已创建（用户名/密码已知）
- [ ] 行情数据源已连接
- [ ] 前端构建无报错（`npm run build` 通过）

### 7.2 执行后检查

- [ ] 5 个核心流程全部通过（无阻塞缺陷）
- [ ] 无 HTTP 500 错误
- [ ] 无未捕获的 JS 异常导致页面崩溃
- [ ] 所有 JWT Token 刷新正常
- [ ] 所有 API 缓存行为符合预期
- [ ] 所有 EmptyState 在无数据时正确展示
- [ ] TabBar 5 个 Tab 全部可正常切换
- [ ] 所有页面免责声明合规
- [ ] 移动端安全区域适配正常

---

## 8. 缺陷等级定义

| 等级 | 定义 | 示例 |
|------|------|------|
| 🔴 P0 - 阻塞 | 核心流程中断，无法继续测试 | 登录失败、下单报 500、Token 刷新死循环导致白屏 |
| 🟡 P1 - 严重 | 功能可用但有明显错误 | 收益率计算错误、K线图数据错位、缓存不清导致脏数据 |
| 🟢 P2 - 一般 | 非核心功能异常 | 动画卡顿、空状态文案缺失、样式错位 |
| ⚪ P3 - 建议 | 体验优化建议 | 加载动画不够流畅、Toast 提示时长偏短 |

---

## 9. 变更记录

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|---------|------|
| 2026-07-07 | 1.0 | 初始版本，覆盖 5 大核心流程 + 18 页面 + 33 个接口 + 16 个组件 | Marvis |
