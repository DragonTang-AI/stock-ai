"""性能监控 Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any

class PerfEntry(BaseModel):
    name: str = Field(..., description="指标名称")
    value: float = Field(..., description="数值")
    unit: str = Field(default="ms", description="单位: ms/percent/fps/mb")
    timestamp: float = Field(..., description="Unix时间戳")
    page: Optional[str] = Field(default="/", description="页面路径")
    tags: Optional[dict] = Field(default=None, description="标签")

class MetricsPayload(BaseModel):
    entries: List[PerfEntry] = Field(..., description="指标列表")
    device_id: Optional[str] = Field(default=None, description="设备ID")
    timestamp: float = Field(..., description="时间戳")

class MetricsResponse(BaseModel):
    success: bool = True
    received: int = 0
