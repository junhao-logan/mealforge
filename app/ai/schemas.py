# app/ai/schemas.py
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class RecipeGenerateRequest(BaseModel):
    """AI 菜谱生成请求(第一版: 从库存生成)。全部可选 —— 结构化选项 + 一句自由文本。"""
    free_text: str | None = Field(default=None, max_length=500)   # 一句补充说明
    cuisine: str | None = Field(default=None, max_length=50)
    goal: str | None = Field(default=None, max_length=50)         # 高蛋白/减脂...
    servings: int | None = Field(default=None, ge=1, le=20)

class MealPlanGenerateRequest(BaseModel):
    """AI 周计划生成请求。生成只出草稿(不落库), 用户预览确认后再 commit。"""
    days: int = Field(default=7, ge=1, le=14)
    meals: list[Literal["breakfast", "lunch", "dinner", "snack"]] = Field(
        default=["lunch", "dinner"], min_length=1
    )
    start_date: date | None = None                 # 默认今天
    free_text: str | None = Field(default=None, max_length=500)
    # 食材来源: 'any'=可用库存没有的(采购补齐); 'inventory'=只用库存能做的, 不够就少排不硬凑
    ingredient_source: Literal["any", "inventory"] = "any"
    # 菜谱来源: 'existing'=只用已有菜谱(阶段A); 'new'=允许 AI 混用已有 + 现编(阶段B)
    recipe_source: Literal["existing", "new"] = "existing"
    # 界面语言: 菜名 / 做法 / 新食材名等生成文字都用它
    language: str | None = Field(default=None, max_length=10)