"""通知 Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime

class NotificationCreate(BaseModel):
    type: str = Field(..., description="通知类型: system/price/selection/advisor/trade")
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="通知内容")
    data: Optional[dict] = Field(default=None, description="跳转携带数据")

class NotificationItem(BaseModel):
    id: str
    type: str
    title: str
    content: str
    created_at: str
    read: bool = False
    data: Optional[dict] = None

class NotificationsPage(BaseModel):
    items: List[NotificationItem] = []
    total: int = 0
    unread_count: int = 0
    limit: int = 20
    offset: int = 0
