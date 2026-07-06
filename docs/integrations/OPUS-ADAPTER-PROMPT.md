# Opus 集成裁决 Prompt 模板（Claude Code Opus / 终端 `claude --model opus`）

> **用途**：基于 Flash 产出的 `*-RECON.md`，验证摘要、纠正错误、定稿薄封装（adapter）契约。  
> **禁止**：重新通读整个 qlib/vnpy 仓库；无 RECON.md 时禁止直接开工 adapter。

---

## 使用方式

1. 确认已有 Flash 侦察报告：
   - `docs/integrations/qlib-RECON.md`
   - `docs/integrations/vnpy-RECON.md`
2. 在 **Cursor 内置终端** 或独立终端执行：
   ```bash
   cd /path/to/ai-stock
   claude --model opus
   ```
3. 复制下方「主 Prompt」，替换占位符，并 `@` 引用 RECON 与少量源文件。
4. 将 Opus 输出保存为：
   - `docs/integrations/qlib-ADAPTER-DESIGN.md`
   - `docs/integrations/vnpy-ADAPTER-DESIGN.md`
5. **实现阶段**（Sonnet）只允许依据 `*-ADAPTER-DESIGN.md`，不得偏离契约。

---

## 主 Prompt（复制使用）

```markdown
你是资深量化平台架构师。Flash 模型已完成开源库定向侦察，你的任务是**验证摘要并定稿我们项目的 adapter 契约**。

## 约束（必须遵守）
1. **优先阅读**侦察报告，不要重新扫描整个开源库。
2. 仅允许额外阅读：
   - RECON 中「不确定项」对应的源文件
   - RECON 中「建议 Opus 重点阅读」的文件
   - **合计 ≤8 个文件**
3. 必须指出 Flash 报告中至少 2 处可能错误或过度简化的地方（若无，说明理由）。
4. 输出 adapter 对外接口（Python Protocol / 抽象边界），**业务层禁止直接 import qlib/vnpy**。
5. 涉及资金、订单、持仓的逻辑，必须附「非法状态转移」与测试建议。
6. 不要写完整实现代码，只写：接口定义、伪代码级流程、风险清单、测试用例标题。

## 输入
- 侦察报告：@{RECON_FILE}
- 我们的一期范围：
  - A 股 + 港股（港股 Gateway 可标为二期占位）
  - 模拟盘优先，实盘 Gateway 仅留接口
  - AI 信号格式见 `docs/contracts/signal.schema.json`（若不存在则在本输出中草案定义）

## 输出格式（严格按此 Markdown 结构）

# {PROJECT} Adapter 设计（Opus 定稿）

- 基于侦察报告：`{RECON_FILE}`
- 库版本：{VERSION}
- 定稿时间：{DATE}

## 1. Flash 报告验证结论
| RECON 条目 | 验证结果（正确/部分正确/错误） | 依据（文件:行号） | 修正说明 |
|------------|-------------------------------|-------------------|----------|
| | | | |

## 2. 集成边界（什么进 wrapper，什么绝不暴露）
### 2.1 我们暴露给业务层的能力
- ...

### 2.2 封装在 wrapper 内部、业务禁止直接调用的
- ...

## 3. Adapter 对外接口（定稿）

### 3.1 Python Protocol / 抽象类
​```python
# 文件建议路径：{ADAPTER_PATH}
from typing import Protocol

class {AdapterName}(Protocol):
    ...
​```

### 3.2 方法契约表
| 方法 | 输入 | 输出 | 幂等 | 异常 | 备注 |
|------|------|------|------|------|------|
| | | | | | |

## 4. 核心流程（序列说明）
### 4.1 初始化流程
1. ...
2. ...

### 4.2 日常调用流程（如：每日选股 / 下单）
1. ...
2. ...

## 5. 状态机（订单/引擎，若有）
​```text
状态：...
合法转移：A -> B
非法转移：...（必须拒绝并抛/返回明确错误）
​```

## 6. 线程 / 事件循环 / 异步约束
- ...
- 与 FastAPI / Celery worker 如何共存：

## 7. 与 AI 信号层的衔接
| signal.schema 字段 | adapter 哪个方法消费 | 转换规则 |
|--------------------|----------------------|----------|
| symbol | | |
| side | | |
| qty | | |
| confidence | | （仅记录，不参与撮合） |

## 8. 风险清单（至少 5 条）
| # | 风险 | 严重性 | 缓解措施 | 测试用例 ID |
|---|------|--------|----------|-------------|
| 1 | | | | |

## 9. 测试策略（只列用例标题，不写完整代码）
### 单元测试
- `test_...`

### 集成测试
- `test_...`

### 对账 / 回归
- ...

## 10. 一期 / 二期切分
| 能力 | 一期 | 二期 |
|------|------|------|
| | | |

## 11. 实现任务拆分（给 Sonnet 的执行清单）
- [ ] 创建 `{ADAPTER_PATH}`
- [ ] ...
- [ ] 禁止修改的文件/目录：

## 12. 开放问题（需人类决策）
- [ ] ...
```

---

## Qlib 专用 Prompt 片段

替换占位符：

| 占位符 | 值 |
|--------|-----|
| `{PROJECT}` | Qlib |
| `{RECON_FILE}` | `docs/integrations/qlib-RECON.md` |
| `{ADAPTER_PATH}` | `backend/quant/qlib_runner.py` |
| `{AdapterName}` | `StockPickRunner` |

**额外要求（粘贴到主 Prompt 末尾）：**

```markdown
## Qlib 专项要求
1. 对外只暴露：`run_daily_pick(market: str, top_n: int) -> list[PickSignal]`，禁止暴露 workflow 内部对象。
2. 明确 `qlib init` 与数据目录（cn_data）的初始化责任：wrapper 内还是部署脚本。
3. 盘后批处理 vs 盘中调用的限制必须写清。
4. Top N 输出字段至少包含：`symbol`, `score`, `rank`, `as_of_date`。
5. LLM 文案生成不在本 adapter 内，只输出结构化分数。
```

---

## VeighNa 专用 Prompt 片段

替换占位符：

| 占位符 | 值 |
|--------|-----|
| `{PROJECT}` | VeighNa (vn.py) |
| `{RECON_FILE}` | `docs/integrations/vnpy-RECON.md` |
| `{ADAPTER_PATH}` | `backend/trader/vnpy_wrapper.py` |
| `{AdapterName}` | `TradeExecutionAdapter` |

**额外要求（粘贴到主 Prompt 末尾）：**

```markdown
## VeighNa 专项要求
1. 模拟盘与实盘必须同一套 `place_order / cancel_order / get_positions / get_account` 接口；切换只改 Gateway 配置。
2. 明确 MainEngine 生命周期：谁启动、谁销毁、是否单例、多用户如何隔离（一期可先单实例）。
3. 订单回报：同步返回 vs 事件回调，如何映射到我们的 `Order` 表状态机。
4. A 股 T+1、涨跌停、最小手数由谁校验：wrapper 必须写明。
5. 一期不接真实 Gateway 时，接口仍要定义 `LiveGateway` 占位 Protocol。
```

---

## Opus 会话推荐 @ 文件列表

### Qlib 裁决会话

```text
@docs/integrations/qlib-RECON.md
@docs/integrations/OPUS-ADAPTER-PROMPT.md
（从 RECON 的「不确定项」挑 ≤5 个源文件）
```

### VeighNa 裁决会话

```text
@docs/integrations/vnpy-RECON.md
@docs/integrations/OPUS-ADAPTER-PROMPT.md
（从 RECON 的「不确定项」挑 ≤5 个源文件）
```

---

## 质量门禁（ADAPTER-DESIGN 定稿前）

- [ ] 已纠正或确认 RECON 中所有 `low` 置信度条目
- [ ] 业务层 `import qlib` / `import vnpy` 出现在「禁止」清单中
- [ ] 订单/持仓相关接口有状态机或等价约束说明
- [ ] 至少 5 条风险 + 对应测试标题
- [ ] 一期/二期边界清晰（实盘 Gateway 不塞进一期实现任务）
- [ ] **人类已审阅** S 级章节（状态机、资金、订单）

---

## 定稿后的实现分工

| 步骤 | 工具 | 模型 |
|------|------|------|
| 按 ADAPTER-DESIGN 写 wrapper | Claude Code 终端 | Sonnet |
| 写 pytest | Claude Code 终端 | Sonnet |
| 测试失败 / 状态机对不上 | Claude Code 终端 | Opus（仍只 @ 相关文件） |
| 前端 / 普通 API | Cursor | Composer / DeepSeek Flash |

---

## 与 HANDOFF.md 的衔接

定稿后在 `docs/HANDOFF.md` 追加：

```markdown
## 集成里程碑
- [x] qlib-RECON.md（Flash）
- [x] qlib-ADAPTER-DESIGN.md（Opus）
- [ ] qlib_runner.py 实现（Sonnet）
- [x] vnpy-RECON.md（Flash）
- [ ] vnpy-ADAPTER-DESIGN.md（Opus）
- [ ] vnpy_wrapper.py 实现（Sonnet）
```
