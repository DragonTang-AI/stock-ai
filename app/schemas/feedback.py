"""用户反馈 Schema"""
from pydantic import BaseModel, Field
from typing import Optional

class FeedbackRequest(BaseModel):
    content: str = Field(..., description="反馈内容")
    contact: Optional[str] = Field(default=None, description="联系方式")
    category: Optional[str] = Field(default="general", description="分类: bug/suggestion/general")
    page_path: Optional[str] = Field(default="/", description="当前页面路径")

class FeedbackResponse(BaseModel):
    success: bool = True
    message: str = "感谢您的反馈！"
