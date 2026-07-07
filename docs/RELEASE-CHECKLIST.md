# AI-Stock V1 发布前检查清单

> 生成日期: 2026-07-07 | 自动扫描 + 人工复核  
> 项目路径: `frontend-ui/frontend/src`  
> 目标版本: V1.0.0

---

## 一、功能完整性检查

### 1.1 Tab 页面

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 行情 Tab (`pages/market/index`) | ❌ 缺失 | `pages.json` 已注册但 `.vue` 文件不存在 |
| 选股 Tab (`pages/selection/index`) | ✅ 已创建 | 文件存在 |
| 持仓 Tab (`pages/portfolio/index`) | ✅ 已创建 | 文件存在 |
| AI助手 Tab (`pages/advisor/index`) | ❌ 缺失 | `pages.json` 已注册但 `.vue` 文件不存在 |
| 我的 Tab (`pages/mine/index`) | ✅ 已创建 | 文件存在 |

**结论**: 5 个 Tab 中有 2 个（行情、AI助手）缺少 `.vue` 文件，需补充实现。

### 1.2 子页面 / 非 Tab 页面

| 页面路径 | 状态 | 说明 |
|---------|------|------|
| `pages/login/index` | ❌ 缺失 | 登录页未实现，`App.vue` 中无条件跳转 |
| `pages/watchlist/index` | ❌ 缺失 | 自选股页未实现 |
| `pages/portfolio/history` | ❌ 缺失 | 交易记录页未实现 |
| `pages/detail/index` | ✅ 已创建 | 行情详情 |
| `pages/selection/detail` | ✅ 已创建 | 选股分析详情 |
| `pages/selection/candidates` | ✅ 已创建 | 候选池 |
| `pages/portfolio/analytics` | ✅ 已创建 | 持仓分析 |
| `pages/hosted/index` | ✅ 已创建 | AI托管 |
| `pages/dashboard/index` | ✅ 已创建 | 数据看板 |
| `pages/broadcast/index` | ✅ 已创建 | 每日播报 |
| `pages/feedback/index` | ✅ 已创建 | 用户反馈 |
| `pages/mine/notifications` | ✅ 已创建 | 消息中心 |
| `pages/mine/settings` | ✅ 已创建 | 设置页 |

**结论**: 5 个核心子页面缺失（登录、行情、AI助手、自选股、交易记录）。

### 1.3 选股流程

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 选股首页 Top5 卡片 | ❌ 未验证 | `selection/index.vue` 存在，需验证功能 |
| 候选池浏览 | ❌ 未验证 | `selection/candidates.vue` 存在 |
| 单股 Agent 分析详情 | ❌ 未验证 | `selection/detail.vue` 存在 |
| API 接入 (`api/selection.ts`) | ✅ 已创建 | 文件存在 |

### 1.4 交易流程

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 下单面板 (OrderPanel) | ✅ 已创建 | `components/trading/OrderPanel.vue` |
| 订单确认 (OrderConfirm) | ✅ 已创建 | `components/trading/OrderConfirm.vue` |
| MarketRule 校验 | ❌ 未验证 | 需确认后端契约对接 |
| API 接入 (`api/trading.ts`) | ✅ 已创建 | 文件存在 |

### 1.5 AI 对话

| 检查项 | 状态 | 说明 |
|--------|------|------|
| AI 诊断页 (`pages/advisor`) | ❌ 缺失 | Tab 页面未实现 |
| 持仓诊断 API (`api/analysis.ts`) | ✅ 已创建 | 文件存在 |
| 托管开关 + 信号日志 (`pages/hosted`) | ✅ 已创建 | 文件存在 |
| 播报 TTS | ❌ 未验证 | `pages/broadcast/index.vue` 存在 |

---

## 二、合规检查

### 2.1 免责声明覆盖

> 扫描所有页面 `.vue` 文件，检查是否包含 `Disclaimer` 组件或免责声明文案。

| 页面 | 免责声明 | 状态 |
|------|---------|------|
| `pages/broadcast/index.vue` | ✅ 有 | 3 处引用 |
| `pages/dashboard/index.vue` | ✅ 有 | 2 处引用 |
| `pages/detail/index.vue` | ❌ 无 | **缺失** |
| `pages/feedback/index.vue` | ❌ 无 | **缺失** |
| `pages/hosted/index.vue` | ✅ 有 | 5 处引用 |
| `pages/mine/index.vue` | ✅ 有 | 2 处引用 |
| `pages/mine/notifications.vue` | ❌ 无 | **缺失** |
| `pages/mine/settings.vue` | ✅ 有 | 2 处引用 |
| `pages/portfolio/analytics.vue` | ✅ 有 | 3 处引用 |
| `pages/portfolio/index.vue` | ✅ 有 | 2 处引用 |
| `pages/selection/candidates.vue` | ❌ 无 | **缺失** |
| `pages/selection/detail.vue` | ❌ 无 | **缺失** |
| `pages/selection/index.vue` | ❌ 无 | **缺失** |

**需修复页面**: `detail/index`, `feedback/index`, `mine/notifications`, `selection/candidates`, `selection/detail`, `selection/index`（共 6 页）。

### 2.2 审核模式

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 审核模式全局开关 | ❌ 不完整 | `App.vue` 引用 `useComplianceStore` 但 **store 文件缺失** |
| AuditBadge 全局组件 | ❌ 缺失 | `App.vue` 引用 `AuditBadge.vue` 但 **文件不存在** |
| 页面级审核模式适配 | ❌ 不完整 | 仅 `hosted/index.vue` 有审核模式相关代码（6处）|

**结论**: 合规基础设施不完整——`compliance` store 和 `AuditBadge.vue` 组件均缺失。

### 2.3 审核文案

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 免责文案内容 | ✅ 合规 | "本平台所有内容仅供学习交流，不构成任何投资建议" |
| 无承诺收益 | ✅ 合规 | 声明"过往业绩不代表未来表现" |
| 后端审核模式 | ✅ 已配置 | `.env.example` 中 `IS_AUDIT_MODE=true` |

---

## 三、性能检查

### 3.1 性能基础设施

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 图片懒加载 (`LazyImage.vue`) | ✅ 已创建 | 组件存在 |
| 虚拟滚动 (`VirtualList.vue`) | ✅ 已创建 | 组件存在 |
| 骨架屏 (`SkeletonScreen.vue`) | ✅ 已创建 | 组件存在 |
| LoadingSkeleton | ✅ 已创建 | 组件存在 |
| API 请求缓存 (`utils/cache.ts`) | ✅ 已创建 | 文件存在 |
| 性能监控 (`utils/perf-monitor.ts`) | ✅ 已创建 | 文件存在 |
| 性能监控 composable | ✅ 已创建 | 文件存在 |
| 图表主题 (`utils/chart-theme.ts`) | ✅ 已创建 | 支持深色/浅色 |
| 动画 (`styles/animations.scss`) | ✅ 已创建 | 文件存在 |

### 3.2 待验证指标

| 指标 | 目标 | 当前状态 |
|------|------|---------|
| 首屏加载时间 | < 2s | ❌ 待实测（无 package.json，无法构建） |
| API 响应时间 | < 1s | ❌ 待实测 |
| 列表滑动帧率 | 60fps | ❌ 待实测 |
| 内存泄漏 | 无 | ❌ 待实测 |

**阻塞问题**: 项目缺少 `package.json`，无法执行 `npm run build` 或 `npm run dev`，性能指标无法实测。

---

## 四、兼容性检查

| 检查项 | 状态 | 说明 |
|--------|------|------|
| iOS Safari | ❌ 待验证 | 无构建产物，无法在真机测试 |
| Android Chrome | ❌ 待验证 | 同上 |
| 微信浏览器 / 小程序 | ❌ 待验证 | 同上 |
| 安全区域适配 | ✅ 已配置 | `pages.json` 中 `safearea` 已定义 |
| 键盘弹出适配 | ✅ 已配置 | `softinputMode: adjustResize` |
| 横竖屏适配 | ❌ 待验证 | K线图需实测 |
| `dist/build/h5` 产物存在 | ✅ 有 | 有历史构建产物 |

---

## 五、安全检查

### 5.1 JWT Token 存储

| 检查项 | 状态 | 说明 |
|--------|------|------|
| Token 存储方式 | ⚠️ 注意 | 使用 `uni.getStorageSync('accessToken')`，非 HttpOnly Cookie |
| Token 自动刷新 | ✅ 已实现 | `request.ts` 401 → 自动刷新 → 重试 |
| Refresh Token 流转 | ⚠️ 注意 | 需确认 refresh token 同样使用 Storage 存储 |

### 5.2 HTTPS

| 检查项 | 状态 | 说明 |
|--------|------|------|
| API Base URL | ✅ HTTPS | `https://stockai.dragontang.com/api/v1` |
| 全链路 HTTPS | ✅ | 前端 `.env` 配置 HTTPS |

### 5.3 敏感信息泄露

| 检查文件 | 结果 |
|---------|------|
| `api/*.ts` (7 个文件) | ✅ 无硬编码密钥/密码 |
| `utils/request.ts` | ✅ Token 从 Storage 动态获取，无硬编码 |
| `utils/*.ts` (其他 10 个文件) | ✅ 无硬编码敏感信息 |
| `frontend/.env` | ⚠️ 暴露后端 API 地址（非敏感但可能暴露架构） |
| `../.env.example` | ⚠️ 包含 `JWT_SECRET=CHANGE_ME`、`DATABASE_URL`（含密码 `postgres:postgres`）、`LLM_API_KEY` 占位符 |
| `app/core/config.py` | ⚠️ `jwt_secret` 默认值 `"CHANGE_ME"` |

**风险项**:
- `.env.example` 中 `DATABASE_URL` 包含明文密码（虽然是示例值，但建议脱敏）
- `JWT_SECRET` 和 `LLM_API_KEY` 在生产环境必须替换

### 5.4 前端静态资源

| 检查项 | 状态 |
|--------|------|
| 前端 `dist/` 中无 `.map` 文件暴露源码 | ❌ 待检查 |
| 无 `console.log` 输出敏感信息 | ❌ 待检查 |

---

## 六、项目工程完整性

### 6.1 构建配置

| 检查项 | 状态 | 说明 |
|--------|------|------|
| `package.json` | ❌ 缺失 | 无法执行 `npm install` / `npm run build` |
| `vite.config.ts/js` | ❌ 缺失 | 构建配置缺失 |
| `tsconfig.json` | ❌ 缺失 | TypeScript 配置缺失 |
| `manifest.json` (uni-app) | ❌ 缺失 | uni-app 项目清单文件缺失 |

### 6.2 状态管理

| 检查项 | 状态 | 说明 |
|--------|------|------|
| `stores/` 目录 | ❌ 空 | `App.vue` 引用 `useAuthStore` / `useComplianceStore` 但均未实现 |
| `useAuthStore` | ❌ 缺失 | 登录态管理缺失 |
| `useComplianceStore` | ❌ 缺失 | 合规审核模式管理缺失 |

### 6.3 静态资源

| 检查项 | 状态 |
|--------|------|
| TabBar 图标 (`static/tabbar/`) | ❌ 待确认 |
| 其他静态资源 | ❌ 待确认 |

### 6.4 测试

| 检查项 | 状态 |
|--------|------|
| 单元测试文件 | ❌ 未找到 |
| 集成测试文件 | ❌ 未找到 |
| E2E 测试 | ❌ 未找到 |

---

## 七、汇总与发布判定

### 7.1 阻塞项（必须解决才能发布）

| # | 问题 | 严重程度 |
|---|------|---------|
| 1 | **5 个页面缺失** `.vue` 文件（login, market, advisor, watchlist, history） | 🔴 阻断 |
| 2 | **`package.json` 缺失**——无法构建部署 | 🔴 阻断 |
| 3 | **`compliance` store + `AuditBadge.vue` 缺失**——合规功能失效 | 🔴 阻断 |
| 4 | **`auth` store 缺失**——登录态管理失效 | 🔴 阻断 |
| 5 | **6 个页面缺少免责声明** | 🟡 高风险 |

### 7.2 告警项（发布前应修复）

| # | 问题 |
|---|------|
| 1 | `.env.example` 中数据库密码明文（示例值，但建议脱敏） |
| 2 | `JWT_SECRET` 默认值 `CHANGE_ME`，生产环境必须更改 |
| 3 | Token 存储在 `StorageSync`，建议生产环境升级为 HttpOnly Cookie |
| 4 | 缺少 `tsconfig.json` 和 `vite.config`，工程规范不完整 |
| 5 | 无任何自动化测试 |

### 7.3 发布判定

| 维度 | 得分 | 说明 |
|------|------|------|
| 功能完整性 | 40% | 14 个注册页面中有 5 个缺失，Tab 缺 2 个 |
| 合规 | 55% | 免责声明覆盖 7/13，审核模式基础设施缺失 |
| 性能 | 待测 | 组件齐全但无法构建实测 |
| 兼容性 | 待测 | 配置齐全但无法构建实测 |
| 安全 | 70% | 无硬编码密钥，但 Token 存储和默认凭据有风险 |
| 工程完整性 | 30% | 缺构建配置、状态管理、测试 |

**总体判定**: ❌ **不建议发布**。核心页面缺失、构建配置缺失、合规基础设施不完整，需完成以下最低发布条件。

---

## 八、发布前最低修复清单

### 必须完成（P0）

- [ ] **T-M041-FIX-01**: 创建 `package.json`、`vite.config.ts`、`tsconfig.json`、`manifest.json`
- [ ] **T-M041-FIX-02**: 实现 `stores/auth.ts` 登录态管理
- [ ] **T-M041-FIX-03**: 实现 `stores/compliance.ts` 合规审核模式管理
- [ ] **T-M041-FIX-04**: 实现 `components/compliance/AuditBadge.vue`
- [ ] **T-M041-FIX-05**: 实现或创建占位页面：`pages/login/index.vue`
- [ ] **T-M041-FIX-06**: 实现或创建占位页面：`pages/market/index.vue`
- [ ] **T-M041-FIX-07**: 实现或创建占位页面：`pages/advisor/index.vue`
- [ ] **T-M041-FIX-08**: 实现或创建占位页面：`pages/watchlist/index.vue`
- [ ] **T-M041-FIX-09**: 实现或创建占位页面：`pages/portfolio/history.vue`

### 强烈建议（P1）

- [ ] **T-M041-FIX-10**: 为 6 个页面添加 `Disclaimer` 免责声明组件
- [ ] **T-M041-FIX-11**: 替换 `.env.example` 中 `JWT_SECRET` 为占位符（不留 `CHANGE_ME` 等可被误用的值）
- [ ] **T-M041-FIX-12**: 确保生产环境部署前替换所有默认凭据

### 建议（P2）

- [ ] **T-M041-FIX-13**: 补充至少冒烟测试用例
- [ ] **T-M041-FIX-14**: 构建后实测首屏性能并记录
- [ ] **T-M041-FIX-15**: 构建后实测 iOS/Android 兼容性

---

*本文档由自动化扫描生成，部分检查项需人工复核确认。*
