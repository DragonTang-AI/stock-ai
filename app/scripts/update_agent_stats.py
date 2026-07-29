"""update_agent_stats.py — 从真实交易数据计算交易员统计指标，更新 agent_traders 表。

数据来源：
- agent_signals（exec_status='confirmed'）→ total_trades
- agent_performances → win_rate, max_drawdown, sharpe_ratio（聚合月度数据）
- salary_curve → annual_return（基于净值曲线计算年化收益）

用法：
    python -m app.scripts.update_agent_stats          # 更新所有交易员
    python -m app.scripts.update_agent_stats <agent_id>  # 更新指定交易员
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from sqlalchemy import select, func, and_
from app.core.database import get_session_factory
from app.models.agent import AgentTrader, AgentSignal, AgentPortfolio, AgentPerformance


async def update_agent_stats(agent_id: str | None = None):
    factory = get_session_factory()
    async with factory() as db:
        # 查询要更新的交易员
        if agent_id:
            q = select(AgentTrader).where(AgentTrader.id == agent_id)
        else:
            q = select(AgentTrader).where(AgentTrader.is_active == True)
        result = await db.execute(q)
        agents = result.scalars().all()

        if not agents:
            label = agent_id if agent_id else "无活跃交易员"
            print(f"未找到交易员: {label}")
            return

        for agent in agents:
            print(f"\n--- 更新交易员: {agent.code_name} ({agent.id}) ---")

            # 1. total_trades: 已确认信号数
            trades_q = select(func.count(AgentSignal.id)).where(
                and_(
                    AgentSignal.trader_id == agent.id,
                    AgentSignal.exec_status == 'confirmed',
                )
            )
            total_trades = (await db.execute(trades_q)).scalar() or 0
            print(f"  total_trades (confirmed signals): {total_trades}")

            # 2. 从 agent_performances 聚合指标
            perf_q = (
                select(AgentPerformance)
                .where(AgentPerformance.agent_id == agent.id)
                .order_by(AgentPerformance.period_end.desc())
                .limit(12)
            )
            perfs = (await db.execute(perf_q)).scalars().all()

            if perfs:
                # win_rate: 最近12个月平均值
                win_rates = [float(p.win_rate) for p in perfs if p.win_rate is not None]
                avg_win_rate = round(sum(win_rates) / len(win_rates), 2) if win_rates else None

                # max_drawdown: 最近12个月最差
                drawdowns = [float(p.max_drawdown) for p in perfs if p.max_drawdown is not None]
                worst_dd = round(min(drawdowns), 2) if drawdowns else None

                # sharpe_ratio: 最近12个月平均值
                sharpes = [float(p.sharpe_ratio) for p in perfs if p.sharpe_ratio is not None]
                avg_sharpe = round(sum(sharpes) / len(sharpes), 2) if sharpes else None

                print(f"  win_rate (avg 12m): {avg_win_rate}")
                print(f"  max_drawdown (worst 12m): {worst_dd}")
                print(f"  sharpe_ratio (avg 12m): {avg_sharpe}")
            else:
                avg_win_rate = None
                worst_dd = None
                avg_sharpe = None
                print("  无 performances 数据")

            # 3. annual_return: 从 salary_curve 计算年化收益
            salary_curve = agent.salary_curve or []

            if salary_curve and len(salary_curve) >= 2:
                first_value = float(salary_curve[0].get("value", 10000))
                last_value = float(salary_curve[-1].get("value", first_value))
                months = len(salary_curve)
                cumulative_return = (last_value - 10000) / 10000 * 100
                years = months / 12
                if years > 0 and first_value > 0:
                    annual_return = round((pow(last_value / 10000, 1 / years) - 1) * 100, 2)
                else:
                    annual_return = round(cumulative_return, 2)
                print(
                    f"  annual_return (salary_curve): {annual_return}% "
                    f"(cumulative: {cumulative_return:.2f}%, months={months})"
                )
            else:
                # fallback: 从 performances 近似年化
                if perfs:
                    returns = [float(p.return_pct) for p in perfs if p.return_pct is not None]
                    avg_monthly = sum(returns) / len(returns) if returns else 0
                    annual_return = round(avg_monthly * 12, 2)
                else:
                    annual_return = None
                print(f"  annual_return (performances fallback): {annual_return}")

            # 4. 更新 agent_traders（有真实数据才覆盖，否则保留种子值）
            updates = {}
            if total_trades is not None and total_trades > 0:
                updates['total_trades'] = total_trades
            if avg_win_rate is not None:
                updates['win_rate'] = avg_win_rate
            if worst_dd is not None:
                updates['max_drawdown'] = worst_dd
            if avg_sharpe is not None:
                updates['sharpe_ratio'] = avg_sharpe
            if annual_return is not None:
                updates['annual_return'] = annual_return

            if updates:
                for field, value in updates.items():
                    setattr(agent, field, value)
                await db.flush()
                print(f"  已更新字段: {list(updates.keys())}")
                for k, v in updates.items():
                    print(f"    {k}: {v}")
            else:
                print("  无数据可更新（保留现有种子值）")

        await db.commit()
        print("\n全部更新完成。")


if __name__ == '__main__':
    agent_id = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(update_agent_stats(agent_id))
