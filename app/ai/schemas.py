# app/ai/schemas.py
from pydantic import BaseModel, Field


class RecipeGenerateRequest(BaseModel):
    """AI 菜谱生成请求(第一版: 从库存生成)。全部可选 —— 结构化选项 + 一句自由文本。"""
    free_text: str | None = Field(default=None, max_length=500)   # 一句补充说明
    cuisine: str | None = Field(default=None, max_length=50)
    goal: str | None = Field(default=None, max_length=50)         # 高蛋白/减脂...
    servings: int | None = Field(default=None, ge=1, le=20)