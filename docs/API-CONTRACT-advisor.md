# API 契约：智能投资助手（Analysis）

**版本**: v1.0
**维护者**: QClaw
**最后更新**: 2026-07-03

---

## 端点总览

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/v1/analysis/diagnose` | JWT | 全面持仓诊断 |
| GET | `/api/v1/analysis/diagnose/{symbol}` | JWT | 单只股票诊断 |
| POST | `/api/v1/analysis/chat/context` | JWT | 问答上下文 |
| GET | `/api/v1/analysis/market/temperature` | JWT | 大盘温度 |

---

## GET /api/v1/analysis/diagnose

**说明**：对当前用户的全部持仓进行全面诊断，同时返回大盘温度。

### 请求
```
GET /api/v1/analysis/diagnose
Authorization: Bearer <token>
```

### 响应 200
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_equity": 99995.0,
      "cash": 94875.0,
      "market_value": 5120.0,
      "total_profit": -5.0,
      "total_profit_pct": -0.01,
      "position_count": 1,
      "win_rate": 0.0,
      "cash_ratio": 94.88
    },
    "positions": [
      {
        "symbol": "000001.SZ",
        "name": "平安银行",
        "quantity": 500,
        "avg_cost": 10.24,
        "current_price": 10.24,
        "profit": 0.0,
        "profit_pct": 0.0,
        "weight": 100.0,
        "rating": "risk",
        "rating_text": "风险",
        "confidence": 27,
        "signals": [
          {
            "type": "bearish",
            "name": "MACD死叉",
            "desc": "MACD柱线=-0.064，空头趋势"
          },
          {
            "type": "bearish",
            "name": "均线空头排列",
            "desc": "MA5 < MA20，短期趋势向下"
          }
        ],
        "action": {
          "action": "reduce",
          "text": "建议减仓",
          "reason": "短期趋势向下，建议减仓控制风险"
        }
      }
    ],
    "risks": [
      {
        "level": "high",
        "title": "持仓过度集中",
        "desc": "单只股票占总仓位100%，建议分散持仓",
        "action": "配置3只以上股票"
      },
      {
        "level": "medium",
        "title": "银行行业敞口过大",
        "desc": "银行板块配置比例过高",
        "action": "适当配置消费、科技等其他行业"
      }
    ],
    "suggestions": [
      {
        "priority": "high",
        "text": "建议减仓平安银行",
        "reason": "短期趋势向下，建议减仓控制风险"
      },
      {
        "priority": "high",
        "text": "持仓过度集中",
        "reason": "单只股票占比过高"
      }
    ],
    "market_temperature": {
      "emoji": "☀️",
      "temperature": "warm",
      "temperature_text": "偏暖",
      "avg_change_pct": 1.22,
      "indices": [
        {"name": "上证指数", "symbol": "sh000001", "price": 4056.78, "change_pct": 0.69},
        {"name": "深证成指", "symbol": "sz399001", "price": 11456.3, "change_pct": 1.58},
        {"name": "创业板指", "symbol": "sz399006", "price": 1782.5, "change_pct": 1.45}
      ]
    },
    "disclaimer": "本分析基于技术面量化指标，仅供参考，不构成投资建议。"
  }
}
```

### 空仓响应 200
```json
{
  "success": true,
  "data": {
    "summary": null,
    "positions": [],
    "risks": [],
    "suggestions": [],
    "market_temperature": { ... },
    "disclaimer": "..."
  }
}
```

---

## GET /api/v1/analysis/diagnose/{symbol}

**说明**：诊断任意一只股票（不限于持仓）。

### 请求
```
GET /api/v1/analysis/diagnose/600519.SH
Authorization: Bearer <token>
```

### 响应 200
```json
{
  "success": true,
  "data": {
    "symbol": "600519.SH",
    "name": "贵州茅台",
    "current_price": 1194.75,
    "rating": "healthy",
    "rating_text": "健康",
    "confidence": 73,
    "signals": [
      {"type": "bullish", "name": "MACD金叉", "desc": "MACD柱线由负转正，多头信号"},
      {"type": "bullish", "name": "均线多头排列", "desc": "MA5 > MA10 > MA20，长期趋势向上"}
    ],
    "action": {
      "action": "hold",
      "text": "继续持有",
      "reason": "趋势向上，基本面良好"
    },
    "indicators": {
      "rsi_6": 58.3,
      "rsi_14": 55.1,
      "macd": 5.42,
      "bollinger_upper": 1220.5,
      "bollinger_middle": 1180.3,
      "bollinger_lower": 1140.1
    }
  }
}
```

---

## POST /api/v1/analysis/chat/context

**说明**：构建问答上下文（供后续 LLM 使用）。

### 请求
```json
{
  "question": "我的持仓健康吗？"
}
```

### 响应 200
```json
{
  "success": true,
  "data": {
    "question": "我的持仓健康吗？",
    "intent": "portfolio_health",
    "context": {
      "has_positions": true,
      "position_count": 1,
      "total_equity": 99995.0,
      "win_rate": 0.0,
      "top_risk": "持仓过度集中",
      "top_suggestion": "建议减仓平安银行"
    }
  }
}
```

---

## GET /api/v1/analysis/market/temperature

**说明**：大盘温度计。

### 响应 200
```json
{
  "success": true,
  "data": {
    "emoji": "☀️",
    "temperature": "warm",
    "temperature_text": "偏暖",
    "avg_change_pct": 1.22,
    "indices": [
      {"name": "上证指数", "symbol": "sh000001", "price": 4056.78, "change_pct": 0.69},
      {"name": "深证成指", "symbol": "sz399001", "price": 11456.3, "change_pct": 1.58},
      {"name": "创业板指", "symbol": "sz399006", "price": 1782.5, "change_pct": 1.45}
    ]
  }
}
```

### 温度等级映射
| temperature | temperature_text | 颜色 |
|-------------|-----------------|------|
| `hot` | 火热 | 红色 |
| `warm` | 偏暖 | 橙色 |
| `neutral` | 中性 | 灰色 |
| `cool` | 偏冷 | 蓝色 |
| `cold` | 冰冷 | 深蓝 |
