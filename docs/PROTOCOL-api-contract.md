# AI-Stock 协作规范 v1.0

**制定者**: QClaw（架构 & 后端主责）
**生效日期**: 2026-07-03
**适用范围**: QClaw × Marvis 双团队所有协作

---

## 一、核心原则

> **范式先行，代码跟上。QClaw 是标准制定者，Marvis 是执行者。**
> 未经 QClaw 确认标准，任何一方不得擅自决定接口格式、字段名、响应结构。

---

## 二、API 契约标准（所有 API 必须遵守）

### 响应格式（铁律）

**所有 API 统一响应格式**：
```json
{
  "success": true,
  "data": <object|array|null>,
  "message": "操作成功"     // 可选，失败时填写
}
```

**分页响应**：
```json
{
  "success": true,
  "data": [...],
  "total": 42,             // 总数
  "page": 1,
  "page_size": 10
}
```

**错误响应**：
```json
{
  "success": false,
  "data": null,
  "message": "余额不足"
}
```

### 禁止出现以下情况

- ❌ 直接返回 list/dict 而不包装 `{success, data}`
- ❌ 返回 `[]` 表示空数据时不带 `success`
- ❌ 同一个项目里有的接口用 `{success, data}` 有的用 `{code, msg, data}`
- ❌ HTTP 状态码和业务状态混用（200 OK + `success: false` 同时出现）

### 命名规范

| 场景 | 规范 | 示例 |
|------|------|------|
| 字段名 | snake_case | `total_equity`, `win_rate` |
| 布尔值 | `is_` 前缀或形容词 | `is_active`, `success` |
| 枚举值 | 英文小写下划线 | `position_count` |
| 金额/数量 | 精确到分/股 | `100025.0`（元），`100`（股） |
| 时间 | ISO 8601 | `2026-07-03T12:00:00Z` |

### 认证

- JWT Bearer Token：所有需要登录的接口加 `Authorization: Bearer <token>`
- Token 通过 `POST /auth/login` 获取，格式见 auth.py
- 前端 `request.ts` 自动在 401 时刷新 token（已实现，保持不变）

---

## 三、开发节奏

```
[QClaw] 写 API 契约文档（字段、格式、示例）
    ↓ 确认后双方各自开发
[QClaw] 实现后端 + 自测（curl 验证所有路由）
[Marvis] 实现前端 + 自测（浏览器验证页面）
    ↓ 都完成后
[QClaw] 发起联调（部署到服务器）
[双方] 共同验收
```

### 每次交付标准

**QClaw 交付后端前必须自测**：
```bash
# 每个新接口都要跑一遍
curl -X POST https://stockai.dragontang.com/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"analytics_test","password":"123456"}'

# 然后用返回的 token 测试受保护接口
curl https://stockai.dragontang.com/api/v1/xxx \
  -H "Authorization: Bearer $TOKEN"
```

**Marvis 交付前端前必须自测**：
```bash
# 构建并本地预览
npm run build
# 验证 dist 里的 JS 中包含了正确的 API 路径
grep -o '/api/v1/xxx' dist/assets/index-*.js
```

---

## 四、联调流程

1. **QClaw 通知 Marvis**：后端某功能已部署，附上 API 路径和响应示例
2. **Marvis 自测接入**：curl 跑通后再写前端代码
3. **Marvis 部署后通知 QClaw**：QClaw 端到端验证（登录→功能→数据）
4. **用户验收**：QClaw 截图确认功能正常后通知用户测试

---

## 五、禁止事项

| 禁止 | 替代方案 |
|------|----------|
| 前端自行定义 API 路径/格式 | 等 QClaw 发 API 契约 |
| 后端自行改变已有字段名 | 发版前通知 Marvis 并更新契约文档 |
| 单方面修改通用组件（request.ts） | 双方协商后 QClaw 统一修改 |
| 改完不验证就交付 | 必须 curl/浏览器自测后再说"完成" |

---

## 六、契约文档位置

`docs/API-CONTRACT.md`（QClaw 维护，每次 API 变更同步更新）
