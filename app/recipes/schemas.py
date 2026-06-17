from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ---------- 入参(创建用,Create 后缀) ----------

class RecipeIngredientCreate(BaseModel):
    """配料入参:用户填'用户单位',克数由后端 D5 换算,不在入参里。"""
    ingredient_id: int
    input_amount: Decimal = Field(gt=0)        # 必须 > 0
    input_unit: str = Field(min_length=1)      # 'g' 或该食材的 default_unit(service 校验)


class RecipeVariantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    purpose_tag: str = "default"
    extra_notes: str | None = None
    instructions: str = Field(min_length=1)
    cooking_time_minutes: int | None = Field(default=None, ge=0)
    difficulty: str | None = None
    servings: int = Field(default=1, ge=1)
    ingredients: list[RecipeIngredientCreate] = Field(min_length=1)  # 至少一条配料


class RecipeCreate(BaseModel):
    """一次性嵌套:建 Recipe 同时带第一个 Variant(含配料)。"""
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    cuisine: str | None = None
    variant: RecipeVariantCreate


# ---------- 出参(读取用,Read 后缀) ----------

class RecipeIngredientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ingredient_id: int
    quantity_grams: Decimal       # 算好的克
    input_amount: Decimal         # 原始输入(D7 显示用)
    input_unit: str


class RecipeVariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    purpose_tag: str
    extra_notes: str | None
    instructions: str
    cooking_time_minutes: int | None
    difficulty: str | None
    servings: int
    # 营养缓存(D6 聚合产出,可能 NULL=不完整)
    total_calories: Decimal | None
    total_protein_g: Decimal | None
    total_carbs_g: Decimal | None
    total_fat_g: Decimal | None
    total_grams: Decimal | None
    nutrition_computed_at: datetime | None
    ingredients: list[RecipeIngredientRead]


class RecipeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
    cuisine: str | None
    source: str
    is_public: bool
    created_at: datetime
    variants: list[RecipeVariantRead]


# 列表页用精简版(不嵌套 variant/配料,避免列表查询拉一堆)
class RecipeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    cuisine: str | None
    source: str