from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.services.llm import generate_advisor_response
from app.services.advisor import get_portfolio_diagnosis, get_market_temperature

router = APIRouter(prefix="/analysis", tags=["智能分析"])

@router.post("/chat")
async def chat_with_advisor(
    question: str,
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
        diagnosis = await get_portfolio_diagnosis(db, current_user.id)
        market_temp = await get_market_temperature()
        
        # 调用 LLM 生成回复
        reply = await generate_advisor_response(
            question=question,
            portfolio_context=diagnosis,
            market_temperature=market_temp
        )
        
        return {
            "success": True,
            "data": {
                "question": question,
                "reply": reply,
                "model": "deepseek-v4-flash",
                "context": {
                    "has_positions": diagnosis.get("summary") is not None,
                    "position_count": diagnosis.get("summary", {}).get("position_count", 0),
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
