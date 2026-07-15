"""事件埋点 Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any

class TrackEvent(BaseModel):
    event_type: str = Field(..., description="事件类型: page_view/action/api_error/js_error/performance")
    event_name: str = Field(..., description="事件名称")
    props: Optional[dict] = Field(default=None, description="事件属性")
    timestamp: float = Field(..., description="事件时间戳")
    page_path: Optional[str] = Field(default="/", description="页面路径")

class BatchPayload(BaseModel):
    events: List[TrackEvent] = Field(..., description="事件列表")
    device_id: str = Field(..., description="设备ID")
    timestamp: float = Field(..., description="批次时间戳")

class EventResponse(BaseModel):
    success: bool = True
    received: int = 0
