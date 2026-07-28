# app/shopping/schemas.py
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShoppingListGenerate(BaseModel):
    """生成清单: 给 source_meal_plan_id(从计划推导窗口) 或 start/end 二选一。"""
    source_meal_plan_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    name: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _need_window_source(self):
        # 没给计划, 又没给完整日期区间 → 无法确定窗口
        if self.source_meal_plan_id is None and (
            self.start_date is None or self.end_date is None
        ):
            raise ValueError(
                "需提供 source_meal_plan_id, 或同时提供 start_date 与 end_date"
            )
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date 不能早于 start_date")
        return self


class ShoppingListItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ingredient_id: int | None
    item_name: str | None
    source: str
    needed_grams: Decimal | None
    add_to_inventory: bool
    is_purchased: bool
    purchased_amount: Decimal | None
    purchased_unit: str | None
    purchased_grams: Decimal | None
    category_override: str | None
    notes: str | None


class ShoppingListRead(BaseModel):
    """清单详情(含条目)。"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str | None
    source_meal_plan_id: int | None
    forecast_start: date | None
    forecast_end: date | None
    status: str
    items: list[ShoppingListItemRead]


class ShoppingListListItem(BaseModel):
    """列表项(精简, 不嵌套条目)。"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str | None
    forecast_start: date | None
    forecast_end: date | None
    status: str