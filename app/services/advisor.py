"""
app.services.advisor — 智能投资助手

基于用户持仓 + 实时行情 + 技术指标，提供个性化投资建议。

能力矩阵：
1. 持仓诊断 — 逐只分析持仓的健康度（趋势/超买超卖/仓位/成本）
2. 操作建议 — 买入/持有/减仓/清仓信号
3. 风险扫描 — 组合层面风险评估（集中度/行业敞口/回撤）
4. 市场温度 — 大盘情绪概览（涨跌比/热度）
5. 智能问答 — 自然语言投资咨询（规则引擎 + 上下文组装）

设计原则：
- 不直接调 LLM API（由前端/中台负责 LLM 调用），后端提供结构化上下文
- 所有建议附带置信度和理由链
- 声明：本建议基于技术面量化分析，不构成投资推荐
"""
import logging
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.user import User
from app.models.trading import Account, Position, Order, Trade
from app.services.market import fetch_realtime_quotes, fetch_stock_detail, fetch_kline
from app.services.trading import get_or_create_account, get_positions, INITIAL_BALANCE
from app.schemas.market import QuoteItem

logger = logging.getLogger(__name__)

# 风险等级阈值
SINGLE_POSITION_MAX_PCT = 15.0  # 单票仓位上限 %
SECTOR_MAX_PCT = 40.0           # 单行业上限 %
PORTFOLIO_LOSS_WARN = -5.0      # 组合亏损预警 %
RSI_OVERBOUGHT = 70             # RSI 超买
RSI_OVERSOLD = 30               # RSI 超卖


async def diagnose_portfolio(db: AsyncSession, user: User) -> dict:
    """
    全面持仓诊断

    返回结构：
    {
        "summary": { 总览 },
        "positions": [ 逐只诊断 ],
        "risks": [ 风险项列表 ],
        "suggestions": [ 操作建议列表 ],
        "market_temperature": { 大盘温度 },
        "disclaimer": "本建议基于技术面量化分析..."
    }
    """
    account = await get_or_create_account(db, user)
    positions = await get_positions(db, user)

    # 组装上下文
    total_market_value = sum(p.market_value for p in positions)
    total_cost = sum(p.cost_amount for p in positions)
    total_equity = float(account.balance) + total_market_value
    total_profit = total_equity - INITIAL_BALANCE
    total_profit_pct = (total_profit / INITIAL_BALANCE) * 100 if INITIAL_BALANCE > 0 else 0

    # 1. 逐只诊断
    position_diagnoses = []
    for p in positions:
        diag = await _diagnose_single_position(p, total_market_value)
        position_diagnoses.append(diag)

    # 2. 风险扫描
    risks = _scan_risks(positions, total_market_value, total_profit_pct, position_diagnoses)

    # 3. 操作建议
    suggestions = _generate_suggestions(position_diagnoses, risks, total_profit_pct)

    # 4. 市场温度
    market_temp = await _get_market_temperature()

    # 5. 汇总
    winning = [p for p in positions if p.profit > 0]
    win_rate = round(len(winning) / len(positions) * 100, 2) if positions else 0

    return {
        "summary": {
            "total_equity": round(total_equity, 2),
            "cash": round(float(account.balance), 2),
            "market_value": round(total_market_value, 2),
            "total_profit": round(total_profit, 2),
            "total_profit_pct": round(total_profit_pct, 4),
            "position_count": len(positions),
            "win_rate": win_rate,
            "cash_ratio": round(float(account.balance) / total_equity * 100, 2) if total_equity > 0 else 0,
        },
        "positions": position_diagnoses,
        "risks": risks,
        "suggestions": suggestions,
        "market_temperature": market_temp,
        "generated_at": datetime.now().isoformat(),
        "disclaimer": "本分析基于技术面量化指标，仅供参考，不构成投资建议。投资有风险，入市需谨慎。",
    }


async def _diagnose_single_position(p: Position, total_market_value: float) -> dict:
    """诊断单只持仓"""
    # 取技术指标
    detail = None
    try:
        detail = await fetch_stock_detail(p.symbol)
    except Exception as e:
        logger.warning(f"获取 {p.symbol} 详情失败: {e}")

    weight = round(float(p.market_value) / total_market_value * 100, 2) if total_market_value > 0 else 0
    profit_pct = round(p.profit_pct, 2)

    # 技术信号
    signals = []
    confidence = 50  # 基础置信度

    if detail:
        # RSI
        rsi_14 = detail.get("rsi_14")
        if rsi_14 is not None:
            if rsi_14 >= RSI_OVERBOUGHT:
                signals.append({"type": "bearish", "name": "RSI超买", "value": rsi_14, "desc": f"RSI(14)={rsi_14}，短期超买，注意回调风险"})
                confidence -= 10
            elif rsi_14 <= RSI_OVERSOLD:
                signals.append({"type": "bullish", "name": "RSI超卖", "value": rsi_14, "desc": f"RSI(14)={rsi_14}，短期超卖，可能存在反弹机会"})
                confidence += 10

        # MACD
        macd_hist = detail.get("macd_hist")
        if macd_hist is not None:
            if macd_hist > 0:
                signals.append({"type": "bullish", "name": "MACD金叉", "value": macd_hist, "desc": f"MACD柱线={macd_hist}，多头趋势"})
                confidence += 8
            else:
                signals.append({"type": "bearish", "name": "MACD死叉", "value": macd_hist, "desc": f"MACD柱线={macd_hist}，空头趋势"})
                confidence -= 8

        # 布林带
        boll_upper = detail.get("boll_upper")
        boll_lower = detail.get("boll_lower")
        boll_mid = detail.get("boll_mid")
        if boll_upper and boll_lower and boll_mid:
            if p.market_price >= boll_upper:
                signals.append({"type": "bearish", "name": "触及布林上轨", "value": p.market_price, "desc": f"股价{p.market_price}触及布林上轨{boll_upper}，短期可能回调"})
                confidence -= 5
            elif p.market_price <= boll_lower:
                signals.append({"type": "bullish", "name": "触及布林下轨", "value": p.market_price, "desc": f"股价{p.market_price}触及布林下轨{boll_lower}，可能存在支撑"})
                confidence += 5

        # 均线趋势
        ma5 = detail.get("ma5")
        ma20 = detail.get("ma20")
        if ma5 and ma20:
            if ma5 > ma20:
                signals.append({"type": "bullish", "name": "均线多头排列", "value": None, "desc": f"MA5({ma5}) > MA20({ma20})，短期趋势向上"})
                confidence += 5
            else:
                signals.append({"type": "bearish", "name": "均线空头排列", "value": None, "desc": f"MA5({ma5}) < MA20({ma20})，短期趋势向下"})
                confidence -= 5

    # 仓位评估
    if weight > SINGLE_POSITION_MAX_PCT:
        signals.append({"type": "warning", "name": "仓位过重", "value": weight, "desc": f"占比{weight}%，超过单票{SINGLE_POSITION_MAX_PCT}%上限，建议减仓分散风险"})
        confidence -= 8

    # 盈亏评估
    if profit_pct > 20:
        signals.append({"type": "info", "name": "盈利较多", "value": profit_pct, "desc": f"浮盈{profit_pct}%，可考虑部分止盈"})
    elif profit_pct < -10:
        signals.append({"type": "warning", "name": "亏损较大", "value": profit_pct, "desc": f"浮亏{profit_pct}%，注意止损纪律"})
        confidence -= 5

    # 生成评级
    confidence = max(10, min(90, confidence))
    if confidence >= 70:
        rating = "healthy"
        rating_text = "健康"
    elif confidence >= 50:
        rating = "neutral"
        rating_text = "中性"
    elif confidence >= 30:
        rating = "caution"
        rating_text = "需关注"
    else:
        rating = "risk"
        rating_text = "风险"

    # 建议动作
    action = _decide_action(signals, profit_pct, weight)
    if action is None:
        pass  # already set

    return {
        "symbol": p.symbol,
        "name": p.name,
        "quantity": p.quantity,
        "cost_price": round(p.cost_price, 2),
        "market_price": round(p.market_price, 2),
        "market_value": round(p.market_value, 2),
        "profit": round(p.profit, 2),
        "profit_pct": profit_pct,
        "weight": weight,
        "rating": rating,
        "rating_text": rating_text,
        "confidence": confidence,
        "signals": signals,
        "action": action,
        "indicators": {
            "rsi_14": detail.get("rsi_14") if detail else None,
            "macd_hist": detail.get("macd_hist") if detail else None,
            "ma5": detail.get("ma5") if detail else None,
            "ma20": detail.get("ma20") if detail else None,
            "boll_upper": detail.get("boll_upper") if detail else None,
            "boll_lower": detail.get("boll_lower") if detail else None,
        } if detail else None,
    }


def _decide_action(signals: list, profit_pct: float, weight: float) -> dict:
    """根据信号决定建议动作"""
    bullish = sum(1 for s in signals if s["type"] == "bullish")
    bearish = sum(1 for s in signals if s["type"] == "bearish")
    warnings = sum(1 for s in signals if s["type"] == "warning")

    if bearish >= 2 and profit_pct < -5:
        return {"action": "reduce", "text": "建议减仓", "reason": f"出现{bearish}个看跌信号且浮亏{profit_pct}%，建议减仓止损"}
    elif bearish >= 2:
        return {"action": "reduce", "text": "建议减仓", "reason": f"出现{bearish}个看跌信号，建议减仓规避风险"}
    elif weight > SINGLE_POSITION_MAX_PCT:
        return {"action": "reduce", "text": "建议减仓", "reason": f"仓位占比{weight}%过高，建议减仓至{SINGLE_POSITION_MAX_PCT}%以内"}
    elif bullish >= 2 and profit_pct < 10:
        return {"action": "hold", "text": "建议持有", "reason": f"出现{bullish}个看涨信号，趋势向好，继续持有"}
    elif bullish >= 2 and profit_pct > 20:
        return {"action": "partial_sell", "text": "建议部分止盈", "reason": f"趋势向好但浮盈{profit_pct}%较高，可考虑卖出部分锁定利润"}
    elif bullish >= 1 and bearish == 0:
        return {"action": "hold", "text": "建议持有", "reason": "技术面偏多，暂无明显风险信号"}
    elif bullish == 0 and bearish == 0:
        return {"action": "hold", "text": "建议持有", "reason": "技术面中性，无明显方向信号"}
    else:
        return {"action": "hold", "text": "建议观望", "reason": "多空信号交织，建议观望等待方向明确"}


def _scan_risks(
    positions: list,
    total_market_value: float,
    total_profit_pct: float,
    diagnoses: list,
) -> list:
    """组合层面风险扫描"""
    risks = []

    # 1. 集中度风险
    if total_market_value > 0:
        sorted_ps = sorted(positions, key=lambda p: p.market_value, reverse=True)
        top1_weight = sorted_ps[0].market_value / total_market_value * 100 if sorted_ps else 0
        top3_weight = sum(p.market_value for p in sorted_ps[:3]) / total_market_value * 100 if len(sorted_ps) >= 1 else 0

        if top1_weight > 30:
            risks.append({
                "level": "high",
                "type": "concentration",
                "title": "持仓过度集中",
                "desc": f"单只持仓占比{top1_weight:.1f}%，超过30%警戒线，一旦回调损失较大",
                "action": "建议分散持仓，单票不超过15-20%",
            })
        elif top3_weight > 70 and len(sorted_ps) > 3:
            risks.append({
                "level": "medium",
                "type": "concentration",
                "title": "Top3 集中度偏高",
                "desc": f"前3大持仓占比{top3_weight:.1f}%，集中度偏高",
                "action": "建议适当均衡配置",
            })

    # 2. 行业集中风险
    sector_map = {}
    for p in positions:
        sector = _guess_sector(p.name, p.symbol)
        sector_map[sector] = sector_map.get(sector, 0) + p.market_value

    for sector, mv in sorted(sector_map.items(), key=lambda x: -x[1]):
        sector_pct = mv / total_market_value * 100 if total_market_value > 0 else 0
        if sector_pct > SECTOR_MAX_PCT:
            risks.append({
                "level": "medium",
                "type": "sector",
                "title": f"{sector}行业敞口过大",
                "desc": f"{sector}行业占比{sector_pct:.1f}%，超过{SECTOR_MAX_PCT}%上限",
                "action": f"建议降低{sector}行业配置，增加其他行业分散风险",
            })

    # 3. 整体亏损
    if total_profit_pct < PORTFOLIO_LOSS_WARN:
        risks.append({
            "level": "high",
            "type": "loss",
            "title": "组合亏损预警",
            "desc": f"组合总亏损{total_profit_pct:.2f}%，已跌破{PORTFOLIO_LOSS_WARN}%熔断线",
            "action": "建议全面审视持仓，考虑减仓止损",
        })

    # 4. 低胜率
    if len(positions) >= 3:
        winning = sum(1 for p in positions if p.profit > 0)
        win_rate = winning / len(positions) * 100
        if win_rate < 33:
            risks.append({
                "level": "medium",
                "type": "win_rate",
                "title": "持仓胜率偏低",
                "desc": f"盈利持仓仅{win_rate:.0f}%（{winning}/{len(positions)}），选股准确率有待提升",
                "action": "建议审视亏损持仓的基本面，及时调仓",
            })

    # 5. 持仓数量过少（不够分散）
    if 0 < len(positions) < 3:
        risks.append({
            "level": "low",
            "type": "diversification",
            "title": "持仓过于集中",
            "desc": f"仅持有{len(positions)}只股票，分散不足",
            "action": "建议持仓3-8只，分散非系统性风险",
        })

    # 6. 空仓提醒
    if len(positions) == 0:
        risks.append({
            "level": "info",
            "type": "empty",
            "title": "空仓状态",
            "desc": "当前无持仓，资金全部为现金",
            "action": "可关注选股推荐，寻找投资机会",
        })

    return risks


def _guess_sector(name: str, symbol: str) -> str:
    """行业分类（与 trading.py 中保持一致）"""
    bank_kw = ["银行", "招商银", "工商", "建设", "农业", "交通", "兴业", "浦发", "平安"]
    tech_kw = ["科技", "技术", "信息", "软件", "电子", "半导体", "通信", "宁德"]
    med_kw = ["医药", "医疗", "生物", "恒瑞", "药", "康"]
    food_kw = ["茅台", "五粮", "食品", "饮料", "白酒", "伊利"]
    fin_kw = ["证券", "保险", "信托", "中国平", "中信", "中金", "东方财"]
    energy_kw = ["石油", "石化", "能源", "煤炭", "电力", "核电", "中国神"]
    manu_kw = ["制造", "机械", "汽车", "比亚迪", "美的", "格力", "海尔"]
    house_kw = ["保利", "万科", "房产", "地产"]

    for kw_list, sector in [
        (bank_kw, "银行"), (tech_kw, "科技"), (med_kw, "医药"),
        (food_kw, "消费"), (fin_kw, "金融"), (energy_kw, "能源"),
        (manu_kw, "制造"), (house_kw, "地产"),
    ]:
        if any(kw in name for kw in kw_list):
            return sector
    return "其他"


async def _get_market_temperature() -> dict:
    """
    大盘温度计：取主要指数的涨跌情况

    指数代码用新浪格式直接调用，避免和个股代码冲突。
    """
    from app.integrations.market_data.sina import SinaAdapter

    # 指数用新浪格式（sh000001=上证指数）
    index_map = {
        "sh000001": "上证指数",
        "sz399001": "深证成指",
        "sz399006": "创业板指",
    }

    try:
        adapter = SinaAdapter()
        # 直接用新浪代码调用，绕过 _to_sina_symbol
        client = await adapter._get_client()
        url = f"http://hq.sinajs.cn/list={','.join(index_map.keys())}"
        resp = await client.get(url)
        resp.raise_for_status()
        text = resp.content.decode("gbk", errors="replace")

        indices = []
        up_count = 0
        total_change = 0

        for line in text.strip().split("\n"):
            if "=" not in line or '""' in line:
                continue
            try:
                left, right = line.split("=", 1)
                sina_code = left.split("_str_")[1].strip()
                fields_str = right.strip().strip(';').strip('"')
                fields = fields_str.split(",")
                if len(fields) < 6:
                    continue
                name = index_map.get(sina_code, fields[0])
                prev_close = float(fields[2])
                price = float(fields[3])
                change = price - prev_close
                change_pct = (change / prev_close * 100) if prev_close else 0.0

                if change_pct > 0:
                    up_count += 1
                total_change += change_pct
                indices.append({
                    "symbol": sina_code,
                    "name": name,
                    "price": round(price, 2),
                    "change_pct": round(change_pct, 2),
                })
            except (ValueError, IndexError) as e:
                logger.warning(f"解析指数行失败: {line[:60]} ({e})")
                continue

        avg_change = round(total_change / len(indices), 2) if indices else 0

        # 温度等级
        if avg_change > 1.5:
            temperature = "hot"
            temperature_text = "强势"
            emoji = "🔥"
        elif avg_change > 0.3:
            temperature = "warm"
            temperature_text = "偏暖"
            emoji = "☀️"
        elif avg_change > -0.3:
            temperature = "neutral"
            temperature_text = "中性"
            emoji = "🌡️"
        elif avg_change > -1.5:
            temperature = "cool"
            temperature_text = "偏冷"
            emoji = "❄️"
        else:
            temperature = "cold"
            temperature_text = "弱势"
            emoji = "🥶"

        return {
            "indices": indices,
            "up_count": up_count,
            "total_count": len(indices),
            "avg_change_pct": avg_change,
            "temperature": temperature,
            "temperature_text": temperature_text,
            "emoji": emoji,
        }
    except Exception as e:
        logger.warning(f"获取大盘温度失败: {e}")
        return {
            "indices": [],
            "up_count": 0,
            "total_count": 0,
            "avg_change_pct": 0,
            "temperature": "unknown",
            "temperature_text": "未知",
            "emoji": "❓",
            "error": str(e),
        }


def _generate_suggestions(diagnoses: list, risks: list, total_profit_pct: float) -> list:
    """生成操作建议清单"""
    suggestions = []

    # 基于个股诊断
    for d in diagnoses:
        action = d.get("action", {})
        act_type = action.get("action", "hold")

        if act_type in ("reduce", "partial_sell"):
            suggestions.append({
                "priority": "high" if act_type == "reduce" else "medium",
                "symbol": d["symbol"],
                "name": d["name"],
                "action": act_type,
                "text": action.get("text", ""),
                "reason": action.get("reason", ""),
                "profit_pct": d["profit_pct"],
                "weight": d["weight"],
            })

    # 基于组合风险
    for r in risks:
        if r["level"] in ("high", "medium") and r.get("action"):
            suggestions.append({
                "priority": r["level"],
                "symbol": None,
                "name": None,
                "action": "adjust",
                "text": r["title"],
                "reason": r["desc"],
                "suggestion": r["action"],
            })

    # 组合层面建议
    if total_profit_pct > 10:
        suggestions.append({
            "priority": "low",
            "symbol": None,
            "name": None,
            "action": "info",
            "text": "组合表现良好",
            "reason": f"总收益率{total_profit_pct:.2f}%，可考虑适度止盈落袋为安",
        })
    elif total_profit_pct < -5:
        suggestions.append({
            "priority": "high",
            "symbol": None,
            "name": None,
            "action": "warn",
            "text": "组合亏损预警",
            "reason": f"总收益率{total_profit_pct:.2f}%，建议审视持仓结构",
        })

    # 按优先级排序
    priority_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    suggestions.sort(key=lambda x: priority_order.get(x.get("priority", "info"), 99))

    return suggestions


async def build_chat_context(db: AsyncSession, user: User, question: str) -> dict:
    """
    构建智能问答上下文（供前端/中台调 LLM 时使用）

    根据用户问题组装相关数据，让 LLM 能给出个性化回答。

    Args:
        question: 用户自然语言问题

    Returns:
        结构化上下文，包含用户持仓、行情、指标、风险等
    """
    portfolio = await diagnose_portfolio(db, user)

    # 提取问题中的股票代码
    mentioned_symbols = _extract_symbols(question)

    # 如果问题提到具体股票，补充该股票的详细数据
    stock_details = {}
    for symbol in mentioned_symbols:
        try:
            detail = await fetch_stock_detail(symbol)
            stock_details[symbol] = {
                "name": detail.get("name"),
                "price": detail.get("price"),
                "change_pct": detail.get("change_pct"),
                "pe_ratio": detail.get("pe_ratio"),
                "market_cap": detail.get("market_cap"),
                "rsi_14": detail.get("rsi_14"),
                "macd_hist": detail.get("macd_hist"),
                "ma5": detail.get("ma5"),
                "ma20": detail.get("ma20"),
                "boll_upper": detail.get("boll_upper"),
                "boll_lower": detail.get("boll_lower"),
            }
        except Exception as e:
            logger.warning(f"获取 {symbol} 详情失败: {e}")

    return {
        "question": question,
        "user_portfolio": {
            "summary": portfolio["summary"],
            "positions": [
                {
                    "symbol": p["symbol"],
                    "name": p["name"],
                    "profit_pct": p["profit_pct"],
                    "weight": p["weight"],
                    "rating": p["rating"],
                    "action": p["action"],
                }
                for p in portfolio["positions"]
            ],
            "risks": portfolio["risks"],
            "suggestions": portfolio["suggestions"],
        },
        "market_temperature": portfolio["market_temperature"],
        "mentioned_stocks": stock_details,
        "generated_at": datetime.now().isoformat(),
    }


def _extract_symbols(text: str) -> list:
    """
    从自然语言中提取股票代码或名称

    支持：
    - 6位数字代码（600519、000001）
    - 带后缀代码（600519.SH、sz000001）
    - 常见股票名称（茅台、平安银行、宁德时代等）
    """
    import re
    symbols = []

    # 匹配 6 位数字代码
    codes = re.findall(r'\b(\d{6})\b', text)
    for code in codes:
        if code.startswith(('60', '68')):
            symbols.append(f"{code}.SH")
        elif code.startswith(('00', '30')):
            symbols.append(f"{code}.SZ")

    # 常见股票名称映射
    name_map = {
        "茅台": "600519.SH", "贵州茅台": "600519.SH",
        "平安": "000001.SZ", "平安银行": "000001.SZ",
        "五粮液": "000858.SZ", "恒瑞": "600276.SH", "恒瑞医药": "600276.SH",
        "宁德": "300750.SZ", "宁德时代": "300750.SZ",
        "美的": "000333.SZ", "美的集团": "000333.SZ",
        "格力": "000651.SZ", "格力电器": "000651.SZ",
        "招行": "600036.SH", "招商银行": "600036.SH",
        "隆基": "601012.SH", "隆基绿能": "601012.SH",
        "中国平安": "601318.SH",
        "工行": "601398.SH", "工商银行": "601398.SH",
        "比亚迪": "002594.SZ",
        "泸州老窖": "000568.SZ",
        "海尔": "600690.SH", "海尔智家": "600690.SH",
        "中信证券": "600030.SH",
        "光大银行": "601818.SH",
    }
    for name, sym in name_map.items():
        if name in text and sym not in symbols:
            symbols.append(sym)

    return list(set(symbols))[:5]  # 最多5只
