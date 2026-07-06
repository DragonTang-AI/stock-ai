# Flash 侦察 Prompt 模板（DeepSeek V4 Flash / 其他轻量模型）

> **用途**：定向阅读 Qlib / VeighNa 源码，产出结构化《侦察报告》，供 Opus 做集成裁决。  
> **禁止**：自由扫描整个仓库、无行号的推测、跳过「不确定项」章节。

---

## 使用方式

1. 先用 `rg` / 目录浏览圈定 **≤20 个文件**（见文末文件清单参考）。
2. 复制下方「主 Prompt」，替换 `{PROJECT}`、`{VERSION}`、`{FILE_LIST}`。
3. 在 Cursor Chat（DeepSeek V4 Flash）中执行，一次只侦察一个库。
4. 将输出保存为：
   - `docs/integrations/qlib-RECON.md`
   - `docs/integrations/vnpy-RECON.md`
5. 把 `RECON.md` 交给 `OPUS-ADAPTER-PROMPT.md` 中的 Opus 会话。

---

## 主 Prompt（复制使用）

```markdown
你是量化交易系统集成工程师，任务是对开源库做**定向代码侦察**（不是架构设计，不是写业务代码）。

## 约束（必须遵守）
1. **只分析**下列文件，禁止扫描或引用列表外的路径：
{FILE_LIST}

2. 每个结论必须标注 **置信度**：`high`（有明确行号）/ `medium`（多文件推断）/ `low`（推测，需 Opus 复查）。
3. 禁止编造不存在的类、函数、配置项；找不到就写「未在本批文件中发现」。
4. 必须输出「不确定项」和「原文摘录」章节，不得省略。
5. 不要给出我们项目的实现代码，只输出侦察报告。

## 项目信息
- 库名称：{PROJECT}
- 版本（pip/git tag）：{VERSION}
- 我们的目标：薄封装接入 AI 选股 + 模拟交易，不 fork 全库

## 输出格式（严格按此 Markdown 结构）

# {PROJECT} 集成侦察报告（Flash 生成，待 Opus 验证）

- 生成时间：{DATE}
- 分析文件数：N
- 库版本：{VERSION}

## 1. 分析范围
（列出实际阅读的文件路径）

## 2. 库的核心职责（3～5 句话）
（本库解决什么问题，与我们哪块能力对应）

## 3. 入口与调用链
| 步骤 | 类/函数 | 文件:行号 | 作用 | 置信度 |
|------|---------|-----------|------|--------|
| 1 | | | | |
| ... | | | | |

## 4. 初始化与配置
| 配置项/环境变量 | 位置（文件:行号） | 默认值/说明 | 置信度 |
|-----------------|-------------------|-------------|--------|
| | | | |

## 5. 与我们一期需求的映射
| 我们需要的 capability | 库内对应实现 | 文件:行号 | 置信度 | 备注 |
|-----------------------|--------------|-----------|--------|------|
| 每日全市场打分 Top N | | | | |
| 输出 symbol + score | | | | |
| 模拟下单 | | | | |
| 查询持仓/资金 | | | | |
| 订单状态回调 | | | | |

## 6. 生命周期与运行时模型
- 进程/线程：...
- 事件循环：...
- 阻塞/异步：...
- 启动顺序：...
（每项标注置信度）

## 7. 边界与异常行为（不要只写 happy path）
| 场景 | 库内行为 | 文件:行号 | 置信度 |
|------|----------|-----------|--------|
| 未初始化就调用 | | | |
| 重复初始化 | | | |
| 网络/数据源失败 | | | |
| 订单非法（卖超、资金不足） | | | |
| Gateway 未连接 | | | |

## 8. 依赖与外部要求
- Python 版本：
- 关键 pip 依赖：
- 外部数据/终端/配置文件：
- 磁盘/内存敏感点：

## 9. 原文摘录（关键 10～30 行，附路径）
### 摘录 1：`path/to/file.py` L120-L145
​```python
（粘贴原文）
​```

（至少 3 段摘录，优先：初始化、核心 API、订单/预测输出）

## 10. 不确定项（强制 Opus 复查）
- [ ] ...
- [ ] ...

## 11. 建议 Opus 重点阅读的 ≤5 个文件
1. ...
2. ...

## 12. 本报告已知局限
（Flash 可能遗漏的点，主动说明）
```

---

## Qlib 专用：文件清单参考（替换 {FILE_LIST}）

侦察前用 `rg` 确认路径存在，按实际仓库调整：

```text
qlib/__init__.py
qlib/config.py
qlib/data/data.py
qlib/data/dataset/__init__.py
qlib/workflow/__init__.py
qlib/workflow/record_temp.py
qlib/contrib/eva/alpha.py
qlib/contrib/data/handler.py
qlib/contrib/model/gbdt.py
examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml
（可选）qlib/tests/ 中与 workflow 相关的 1～2 个测试文件
```

**{PROJECT}** = `Qlib`  
**一期目标关键词**：`qlib init` → 数据 handler → Alpha158 特征 → 模型 predict → 全市场 score 排序 Top N

---

## VeighNa (vn.py) 专用：文件清单参考（替换 {FILE_LIST}）

```text
vnpy/trader/engine.py
vnpy/trader/object.py
vnpy/trader/constant.py
vnpy/trader/utility.py
vnpy/trader/gateway.py
vnpy/trader/app.py
vnpy/trader/event.py
examples/veighna_trader/run.py
（若有）vnpy_paperaccount 或 PaperAccount 相关模块路径
（若有）vnpy_ctastrategy 中与 send_order 相关的 1～2 个文件
```

**{PROJECT}** = `VeighNa (vn.py)`  
**一期目标关键词**：MainEngine → PaperAccount / 仿真 Gateway → `send_order` → 持仓/资金查询 → 订单事件

> 注意：vn.py 版本与扩展包名因安装方式而异，侦察前先执行 `pip show vnpy` 并在报告中写明版本。

---

## 质量自检（保存 RECON.md 前）

- [ ] 每个 `high` 结论都有 `文件:行号`
- [ ] 「不确定项」至少 3 条
- [ ] 「原文摘录」至少 3 段
- [ ] 未出现列表外路径的引用
- [ ] 未包含我们项目的 wrapper 实现代码

---

## 失败时怎么做

| 现象 | 处理 |
|------|------|
| Flash 输出幻觉 API | 删掉无行号条目，缩小文件列表重跑 |
| 单次上下文不够 | 拆成两批侦察，合并到同一 RECON.md |
| 调用链断裂 | 在「不确定项」标注，交给 Opus 补读 ≤5 个文件 |
