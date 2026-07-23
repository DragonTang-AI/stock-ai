"""seed_agents.py — 交易员种子数据"""
import asyncio
import sys
sys.path.insert(0, "/data/stockai/backend")
from app.core.database import get_engine
from sqlalchemy import text

SEED_DATA = [
    {
        "id": "zhenyue",
        "code_name": "镇岳",
        "tag": "价值猎手",
        "description": "镇岳师承价值投资三巨头——巴菲特、格雷厄姆、芒格，专注于寻找被市场低估的优质企业。通过深度基本面分析，挖掘具有安全边际的长期投资标的。适合追求稳健增长的长期投资者。",
        "strategy_detail": "策略以深度价值投资为核心：(1) 市净率<1.5、市盈率<15的低估值筛选；(2) 连续5年股息率>3%的高股息标的；(3) 资产负债率<50%的财务健康企业；(4) 自由现金流为正的经营稳健公司；(5) 行业龙头且ROE连续3年>15%。",
        "masters": "沃伦·巴菲特 · 本杰明·格雷厄姆 · 查理·芒格",
        "hire_price_points": 30,
        "profit_share_pct": 15.0,
        "sort_order": 1,
        "annual_return": 18.5,
        "max_drawdown": -15.2,
        "sharpe_ratio": 1.45,
        "win_rate": 72.5,
        "total_trades": 386,
    },
    {
        "id": "zhuguang",
        "code_name": "逐光",
        "tag": "成长先锋",
        "description": "逐光师承凯西·伍德、彼得·林奇和费雪，专精于挖掘高成长潜力企业。聚焦科技、新能源、生物医药等高景气赛道，寻找未来3-5年具备十倍增长潜力的颠覆性公司。适合风险承受能力较高的投资者。",
        "strategy_detail": "策略以成长投资为核心：(1) 营收增速连续3年>30%的高成长企业；(2) 研发投入占比>15%的技术驱动公司；(3) 市占率处于快速提升期的行业新锐；(4) 赛道规模百亿级以上的新兴行业；(5) PEG<1的合理估值成长股。",
        "masters": "凯西·伍德 · 彼得·林奇 · 菲利普·费雪",
        "hire_price_points": 30,
        "profit_share_pct": 18.0,
        "sort_order": 2,
        "annual_return": 25.8,
        "max_drawdown": -22.6,
        "sharpe_ratio": 1.62,
        "win_rate": 65.3,
        "total_trades": 512,
    },
    {
        "id": "qianji",
        "code_name": "千机",
        "tag": "量化大师",
        "description": "千机师承西蒙斯和量化分析学派，以数学模型和统计套利为核心武器。通过多因子模型、趋势追踪、均值回归等多种策略组合，在不同市场环境中寻找超额收益机会。适合相信数据与模型的理性投资者。",
        "strategy_detail": "策略以量化模型为核心：(1) 多因子Alpha模型（动量/质量/价值/低波四因子加权）；(2) 统计套利：配对交易+跨ETF套利；(3) 趋势追踪：自适应均线+动量突破；(4) 风险平价：动态调整行业/风格暴露；(5) 机器学习辅助信号生成。",
        "masters": "詹姆斯·西蒙斯 · 量化分析学派",
        "hire_price_points": 40,
        "profit_share_pct": 20.0,
        "sort_order": 3,
        "annual_return": 22.1,
        "max_drawdown": -12.8,
        "sharpe_ratio": 1.88,
        "win_rate": 58.7,
        "total_trades": 1246,
    },
    {
        "id": "nichuan",
        "code_name": "逆川",
        "tag": "逆向猎手",
        "description": "逆川师承迈克尔·伯里、塔勒布和阿克曼，擅长在市场恐慌中寻找机会。奉行反脆弱哲学，在市场极度悲观时逆势布局，通过深度价值挖掘和事件驱动策略捕捉极端定价偏差。适合有独立思考能力的逆向投资者。",
        "strategy_detail": "策略以逆向投资为核心：(1) 市场恐慌指数（VIX/ML）处于历史高位时逐步建仓；(2) 机构大幅减持但基本面未恶化的错杀股；(3) 黑天鹅事件后过度反应的优质资产；(4) 困境反转：行业周期底部+企业重组预期；(5) 尾部风险对冲：期权保护+仓位控制。",
        "masters": "迈克尔·伯里 · 纳西姆·塔勒布 · 比尔·阿克曼",
        "hire_price_points": 35,
        "profit_share_pct": 18.0,
        "sort_order": 4,
        "annual_return": 28.3,
        "max_drawdown": -25.5,
        "sharpe_ratio": 1.35,
        "win_rate": 55.2,
        "total_trades": 224,
    },
    {
        "id": "shouyi",
        "code_name": "守一",
        "tag": "全能管家",
        "description": "守一融合了现代资产配置理论与多家大师精华，以全天候策略为核心。通过大类资产配置、行业分散投资和风险预算管理，在不同市场环境下追求稳健回报。适合追求一站式资产配置管理的投资者。",
        "strategy_detail": "策略以资产配置为核心：(1) 大类资产轮动：股票/债券/商品/现金四象限；(2) 行业均衡配置：每个行业上限20%；(3) 风险预算：基于波动率动态调整权重；(4) 再平衡机制：偏离阈值>5%触发；(5) 防御层：市场下行时自动增配债券/现金。",
        "masters": "资产配置理论 · 现代组合管理 · 全天候策略",
        "hire_price_points": 50,
        "profit_share_pct": 12.0,
        "sort_order": 5,
        "annual_return": 15.2,
        "max_drawdown": -10.5,
        "sharpe_ratio": 1.55,
        "win_rate": 78.3,
        "total_trades": 168,
    },
]


async def seed():
    engine = get_engine()
    async with engine.begin() as conn:
        for item in SEED_DATA:
            result = await conn.execute(
                text("SELECT 1 FROM agent.agent_traders WHERE id = :id"),
                {"id": item["id"]},
            )
            if result.fetchone():
                print(f"  - {item['code_name']}({item['id']}) 已存在，跳过")
                continue
            await conn.execute(
                text("""
                INSERT INTO agent.agent_traders
                    (id, code_name, tag, description, strategy_detail, masters,
                     hire_price_points, profit_share_pct, sort_order,
                     annual_return, max_drawdown, sharpe_ratio, win_rate, total_trades)
                VALUES
                    (:id, :code_name, :tag, :description, :strategy_detail, :masters,
                     :hire_price_points, :profit_share_pct, :sort_order,
                     :annual_return, :max_drawdown, :sharpe_ratio, :win_rate, :total_trades)
                """),
                item,
            )
            print(f"  + {item['code_name']}({item['id']}) 已写入")
    print("\n种子数据写入完成！")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
