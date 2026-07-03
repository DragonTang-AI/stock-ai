"""
app.schemas.stock — 股票收藏域 API 数据模型
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class WatchlistItem(BaseModel):
    """自选股条目"""
    id: int
    symbol: str = Field(..., description="股票代码，如 600519.SH")
    name: str = Field("", description="股票名称（从行情接口补充）")
    price: Optional[float] = Field(None, description="最新价（从行情接口补充）")
    change_pct: Optional[float] = Field(None, description="涨跌幅 %（从行情接口补充）")
    note: Optional[str] = Field(None, description="用户备注")
    sort_order: int = Field(0, description="排序序号")
    created_at: datetime


class WatchlistCreate(BaseModel):
    """添加自选股"""
    symbol: str = Field(..., min_length=5, max_length=20, pattern=r"^[A-Z0-9]+\.[SHZSZHK]+$",
                        description="股票代码，格式如 600519.SH / 000001.SZ / 0700.HK")
    note: Optional[str] = Field(None, max_length=100, description="备注")


class WatchlistUpdate(BaseModel):
    """更新自选股"""
    note: Optional[str] = Field(None, max_length=100, description="备注")
    sort_order: Optional[int] = Field(None, ge=0, le=9999, description="排序序号")


class WatchlistResponse(BaseModel):
    """自选股列表响应"""
    success: bool
    data: List[WatchlistItem] = Field(default_factory=list)
    total: int = 0


class WatchlistAddResponse(BaseModel):
    """添加自选股响应"""
    success: bool
    data: WatchlistItem
    message: str = "添加成功"


class WatchlistRemoveResponse(BaseModel):
    """删除自选股响应"""
    success: bool
    message: str = "删除成功"


class WatchlistBatchRequest(BaseModel):
    """批量添加自选股"""
    symbols: List[str] = Field(..., min_length=1, max_length=50,
                                description="股票代码列表，最多 50 只")


class WatchlistCheckRequest(BaseModel):
    """检查某只股票是否在自选"""
    symbol: str = Field(..., min_length=5, max_length=20)


class WatchlistCheckResponse(BaseModel):
    """自选检查响应"""
    success: bool
    is_watching: bool
