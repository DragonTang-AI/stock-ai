import os
import httpx
import json
from typing import AsyncIterator, Optional


def _get_deepseek_config():
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    api_url = os.environ.get("DEEPSEEK_API_URL") or os.getenv("DEEPSEEK_API_URL") or "https://api.deepseek.com/v1"
    model = os.environ.get("DEEPSEEK_MODEL") or os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-flash"
    return {"api_key": api_key, "api_url": api_url, "model": model}


async def stream_text_sse(text: str) -> AsyncIterator[str]:
    """将文本分片通过 SSE 发送（避免 async generator GC 问题）"""
    # 分段发送，每段几个字符
    for i in range(0, len(text), 3):
        chunk = text[i:i+3]
        yield f"data: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"
        # 不加 await，让它快速发送
    yield "data: [DONE]\n\n"


async def chat_completion(
    messages: list[dict],
    model: Optional[str] = None,
    temperature: float = 0.7,
    stream: bool = False
) -> str:
    config = _get_deepseek_config()
    if not config["api_key"]:
        raise ValueError("DEEPSEEK_API_KEY not configured")
    
    url = f"{config['api_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model or config["model"],
        "messages": messages,
        "temperature": temperature,
        "stream": stream
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def build_messages_for_advisor(question: str, portfolio_context: dict, market_temperature: dict) -> list[dict]:
    system_prompt = """你是 AI-Stock 智能投资助手，基于用户持仓和大盘数据提供专业分析。规则：1.用中文回答 2.基于数据不编造 3.给出具体建议 4.加上风险提示"""
    
    positions = portfolio_context.get('positions', [])
    risks = portfolio_context.get('risks', [])
    suggestions = portfolio_context.get('suggestions', [])
    summary = portfolio_context.get('summary', {})
    
    positions_str = _format_positions(positions)
    risks_str = _format_risks(risks)
    suggestions_str = _format_suggestions(suggestions)
    
    user_prompt = f"""用户问题：{question}
用户持仓概况：总资产={summary.get('total_equity','N/A')}, 持仓数量={summary.get('position_count',0)}只, 胜率={summary.get('win_rate',0)}%, 现金比例={summary.get('cash_ratio',0)}%
持仓详情：{positions_str}
风险提醒：{risks_str}
操作建议：{suggestions_str}
大盘温度：{market_temperature.get('temperature_text','N/A')}({market_temperature.get('avg_change_pct',0)}%)
请回答用户问题。"""
    
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]


def _format_positions(positions):
    if not positions:
        return "无持仓"
    return "\n".join([f"- {p.get('name','?')}({p.get('symbol','?')}): {p.get('profit_pct',0):.2f}%" for p in positions])

def _format_risks(risks):
    if not risks:
        return "无风险提醒"
    return "\n".join([f"- [{r.get('level','info')}] {r.get('title','')}: {r.get('desc','')}" for r in risks])

def _format_suggestions(suggestions):
    if not suggestions:
        return "无操作建议"
    return "\n".join([f"- {s.get('text','')}: {s.get('reason','')}" for s in suggestions])


async def generate_advisor_response(question: str, portfolio_context: dict, market_temperature: dict, model: Optional[str] = None) -> str:
    messages = await build_messages_for_advisor(question, portfolio_context, market_temperature)
    return await chat_completion(messages, model=model)


async def generate_streaming_response(question: str, portfolio_context: dict, market_temperature: dict, model: Optional[str] = None) -> AsyncIterator[str]:
    """生成流式回复 - 先获取完整内容再分片 SSE"""
    messages = await build_messages_for_advisor(question, portfolio_context, market_temperature)
    reply = await chat_completion(messages, model=model)
    # 分片 SSE 发送
    for i in range(0, len(reply), 3):
        chunk = reply[i:i+3]
        yield f"data: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"
