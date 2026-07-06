"""
app/integrations — 外部数据源/服务集成层

设计原则：
1. 抽象优先：所有外部依赖通过 Protocol/ABC 暴露
2. 降级友好：每个集成至少有 1 个 fallback 实现
3. 接口稳定：业务层只依赖 base.py 中的接口，不直接 import 具体实现
4. 可替换：factory.py 根据 ENV 决定用哪个实现，便于测试和切换

目录结构：
  market_data/   行情数据源（新浪/AkShare/Tushare...）
"""
