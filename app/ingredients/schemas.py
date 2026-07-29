from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class IngredientRead(BaseModel):
    # from_attributes=True: 允许直接把 SQLAlchemy ORM 对象塞进来转换,
    # 不用手动 .dict() —— 跟 UserRead 一致
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str | None
    # 营养四宏量: 全 Optional, None 表示"该食材无此数据"(D2: 0 ≠ unknown)
    per_100g_calories: Decimal | None
    per_100g_protein: Decimal | None
    per_100g_carbs: Decimal | None
    per_100g_fat: Decimal | None
    # 单位元数据: 前端展示"1 个 / 1 杯"时要用
    default_unit: str
    grams_per_unit: Decimal
    # 可见性(I11): 'private'(自建, 仅自己可见) / 'global'(共享)
    # 前端可据此打"私人创建"标签
    visibility: str


class IngredientCreate(BaseModel):
    """用户自建食材(I11): 服务端固定 source='user'、visibility='private'、
    created_by_user_id=当前用户; 这些不由客户端传。"""
    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=50)
    per_100g_calories: Decimal | None = Field(default=None, ge=0)
    per_100g_protein: Decimal | None = Field(default=None, ge=0)
    per_100g_carbs: Decimal | None = Field(default=None, ge=0)
    per_100g_fat: Decimal | None = Field(default=None, ge=0)
    default_unit: str = Field(default="g", max_length=20)
    grams_per_unit: Decimal = Field(default=Decimal("1.0"), gt=0)
    shelf_life_days: int | None = Field(default=None, ge=0)