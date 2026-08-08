# app/ai/schemas.py
from datetime import date

from pydantic import BaseModel, Field


class RecipeGenerateRequest(BaseModel):
    """AI 菜谱生成请求(第一版: 从库存生成)。全部可选 —— 结构化选项 + 一句自由文本。"""
    free_text: str | None = Field(default=None, max_length=500)   # 一句补充说明
    cuisine: str | None = Field(default=None, max_length=50)
    goal: str | None = Field(default=None, max_length=50)         # 高蛋白/减脂...
    servings: int | None = Field(default=None, ge=1, le=20)

class MealPlanGenerateRequest(BaseModel):
    """AI 周计划生成请求(Week 8 第一版: 从已有菜谱排布)。"""
    days: int = Field(default=7, ge=1, le=14)
    meals: list[str] = Field(default=["lunch", "dinner"])
    start_date: date | None = None                 # 默认今天
    free_text: str | None = Field(default=None, max_length=500)