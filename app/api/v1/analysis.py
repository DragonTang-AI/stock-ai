"""
app.api.v1.analysis.py — 智能投资助手路由

端点：
- GET  /diagnose          全面试仓诊断
- GET  /diagnose/{symbol} 单只持仓诊断
- POST /chat/context      构建问答上下文（供 LLM 使用）
- GET  /market/temperature 大盘温度计
"""
import logging
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional, AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.schemas.advisor import PortfolioDiagnosisResponse, ChatContextResponse, ChatRequest
from app.services.advisor import diagnose_portfolio, build_chat_context, _get_market_temperature as _get_temp
from app.services.llm import generate_streaming_response
from app.services.market import fetch_stock_detail

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/diagnose", response_model=PortfolioDiagnosisResponse)
async def get_portfolio_diagnosis(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    全面持仓诊断

    返回：
    - summary: 账户总览（资产/盈亏/胜率/现金比例）
    - positions: 逐只持仓诊断（评级/信号/建议动作）
    - risks: 风险项列表（集中度/行业/亏损/胜率）
    - suggestions: 操作建议清单（按优先级排序）
    - market_temperature: 大盘温度（上证/深证/创业板）
    - disclaimer: 免责声明
    """
    try:
        result = await diagnose_portfolio(db, current_user)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"持仓诊断失败: {e}", exc_info=True)
        return {"success": False, "data": None, "error": str(e)}


@router.get("/diagnose/{symbol}", response_model=PortfolioDiagnosisResponse)
async def diagnose_single_stock(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    单只股票诊断（不需持仓，任意股票均可）

    返回该股票的技术面分析：
    - 行情数据
    - RSI / MACD / 布林带 / 均线
    - 技术信号列表
    - 评级
    """
    try:
        detail = await fetch_stock_detail(symbol)
        if not detail:
            return {"success": False, "data": None, "error": f"未找到 {symbol}"}

        # 复用信号逻辑
        from app.services.advisor import _diagnose_single_position
        from app.models.trading import Position
        from decimal import Decimal

        # 构造一个临时 Position 对象
        fake_pos = Position(
            symbol=symbol,
            name=detail.get("name", symbol),
            quantity=100,
            cost_price=Decimal(str(detail.get("price", 0))),
            market_price=Decimal(str(detail.get("price", 0))),
            market_value=Decimal(str(detail.get("price", 0) * 100)),
            profit=Decimal("0"),
            profit_pct=Decimal("0"),
            cost_amount=Decimal(str(detail.get("price", 0) * 100)),
        )

        diag = await _diagnose_single_position(fake_pos, detail.get("price", 0) * 100)

        return {
            "success": True,
            "data": {
                "stock": {
                    "symbol": symbol,
                    "name": detail.get("name"),
                    "price": detail.get("price"),
                    "change_pct": detail.get("change_pct"),
                    "pe_ratio": detail.get("pe_ratio"),
                    "market_cap": detail.get("market_cap"),
                },
                "indicators": diag.get("indicators"),
                "signals": diag.get("signals"),
                "rating": diag.get("rating"),
                "rating_text": diag.get("rating_text"),
                "confidence": diag.get("confidence"),
                "action": diag.get("action"),
            },
        }
    except Exception as e:
        logger.error(f"单股诊断失败 {symbol}: {e}", exc_info=True)
        return {"success": False, "data": None, "error": str(e)}


@router.post("/chat/context", response_model=ChatContextResponse)
async def get_chat_context(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    构建智能问答上下文

    前端调用此接口获取结构化上下文，然后连同用户问题一起发给 LLM，
    LLM 基于上下文给出个性化回答。

    上下文包含：
    - 用户持仓概览
    - 风险项
    - 操作建议
    - 大盘温度
    - 问题中提到的股票详情
    """
    try:
        ctx = await build_chat_context(db, current_user, req.question)
        return {"success": True, "data": ctx}
    except Exception as e:
        logger.error(f"构建问答上下文失败: {e}", exc_info=True)
        return {"success": False, "data": None, "error": str(e)}


@router.get("/market/temperature")
async def get_market_temperature(
    current_user: User = Depends(get_current_user),
):
    """
    大盘温度计

    返回上证指数、深证成指、创业板指的涨跌情况及温度等级。
    """
    temp = await _get_temp()
    return {"success": True, "data": temp}

from app.services.llm import generate_advisor_response

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    message: Optional[str] = None

@router.post("/chat", response_model=ChatResponse)
async def chat_with_advisor(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI 投资助手对话（接入 DeepSeek LLM）
    
    - 获取用户持仓诊断
    - 获取大盘温度
    - 调用 DeepSeek 生成自然语言回复
    """
    try:
        # 获取诊断数据
        diagnosis_data = await diagnose_portfolio(db, current_user)
        market_temp = await _get_temp()
        
        # 调用 LLM 生成回复
        reply = await generate_advisor_response(
            question=req.question,
            portfolio_context=diagnosis_data.get("data", {}),
            market_temperature=market_temp
        )
        
        return {
            "success": True,
            "data": {
                "question": req.question,
                "reply": reply,
                "model": "deepseek-v4-flash",
                "context": {
                    "has_positions": diagnosis_data.get("data", {}).get("summary") is not None,
                    "position_count": diagnosis_data.get("data", {}).get("summary", {}).get("position_count", 0),
                    "temperature": market_temp.get("temperature_text")
                }
            }
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"AI 助手暂时不可用: {str(e)}"
        }


# ==================== SSE 流式对话 ====================
class ChatStreamRequest(BaseModel):
    question: str
    model: Optional[str] = "deepseek-v4-flash"


def _call_deepseek_sync(question: str, portfolio_context: dict, market_temperature: dict, model: str) -> str:
    """在线程池中同步调用 DeepSeek（避免 async generator GC 递归）"""
    import httpx
    import os
    import json as _json
    
    api_key = os.environ.get("DEEPSEEK_API_KEY") or ""
    api_url = os.environ.get("DEEPSEEK_API_URL") or "https://api.deepseek.com/v1"
    
    positions = portfolio_context.get('positions', [])
    summary = portfolio_context.get('summary', {})
    positions_str = "\n".join([
        f"- {p.get('name','?')}({p.get('symbol','?')}): {p.get('profit_pct',0):.2f}%"
        for p in positions
    ]) if positions else "无持仓"
    
    system_prompt = "你是AI-Stock智能投资助手，用中文回答。基于用户提供的数据进行分析，给出建议和风险提示。"
    user_prompt = f"""用户问题：{question}
持仓情况：{positions_str}
账户总资产：{summary.get('total_equity','N/A')}元，胜率：{summary.get('win_rate',0)}%，现金比例：{summary.get('cash_ratio',0)}%
大盘温度：{market_temperature.get('temperature_text','N/A')}({market_temperature.get('avg_change_pct',0)}%)
请回答用户问题。"""
    
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    
    url = f"{api_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model or "deepseek-v4-flash", "messages": messages, "temperature": 0.7}
    
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


@router.post("/chat/stream")
async def chat_stream(
    req: ChatStreamRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI 投资助手流式对话（SSE）
    
    返回流式响应，逐 token 输出
    格式: data: {"token": "xxx"}\n\n
    结束: data: [DONE]\n\n
    """
    from fastapi.responses import StreamingResponse
    import json
    import asyncio
    
    async def event_generator() -> AsyncIterator[str]:
        # 1. 获取诊断数据（async IO）
        diagnosis_data = await diagnose_portfolio(db, current_user)
        market_temp = await _get_temp()
        portfolio_ctx = diagnosis_data.get("data", {})
        
        # 2. 在线程池中调用 DeepSeek（同步 HTTP）
        loop = asyncio.get_running_loop()
        reply = await loop.run_in_executor(
            None,
            _call_deepseek_sync,
            req.question,
            portfolio_ctx,
            market_temp,
            req.model or "deepseek-v4-flash"
        )
        
        # 3. 分片 SSE 发送（纯内存）
        for i in range(0, len(reply), 3):
            yield f"data: {json.dumps({'token': reply[i:i+3]}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

    
