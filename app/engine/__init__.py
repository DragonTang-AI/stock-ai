"""
app/engine/ — ai-hedge-fund 交易引擎包装层

模块：
- hedge_fund_client: ai-hedge-fund 调用客户端
- signal_generator:  信号生成器（真实引擎 + mock fallback）
- market_data:       A 股数据适配器
- risk_manager:      风控规则
- scheduler:         定时调度器
"""
