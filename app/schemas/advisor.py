"""
app.schemas.advisor — 智能投资助手 API 数据模型
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class PortfolioDiagnosisResponse(BaseModel):
    """持仓诊断响应"""
    success: bool
    data: Optional[dict] = None


class ChatContextResponse(BaseModel):
    """问答上下文响应"""
    success: bool
    data: Optional[dict] = None


class ChatRequest(BaseModel):
    """投资问答请求"""
    question: str = Field(..., min_length=1, max_length=500, description="用户问题")
    context: Optional[dict] = Field(None, description="前端附加上下文（如当前页面）")
