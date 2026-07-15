"""定时播报 Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any

class BroadcastRecommendation(BaseModel):
    symbol: str
    name: str
    confidence: float
    reason: str

class BroadcastContent(BaseModel):
    overview: str = ""
    recommendations: List[BroadcastRecommendation] = []
    risk_warnings: str = ""

class BroadcastItem(BaseModel):
    id: str
    date: str
    created_at: str
    title: str
    content: BroadcastContent
    audio_url: Optional[str] = None
    duration: Optional[float] = None

class BroadcastListResponse(BaseModel):
    items: List[BroadcastItem] = []
    total: int = 0
    has_prev: bool = False
    has_next: bool = False
