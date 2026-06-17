from decimal import Decimal
from pydantic import BaseModel, ConfigDict


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