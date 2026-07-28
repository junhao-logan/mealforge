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


class ShoppingItemCreate(BaseModel):
    """手动加一条采购项(食材项 或 纯文本项如"厨房纸")。"""
    ingredient_id: int | None = None
    item_name: str | None = Field(default=None, max_length=100)
    needed_grams: Decimal | None = Field(default=None, gt=0)
    add_to_inventory: bool = True
    category_override: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _identity(self):
        # 与 DB 的 ck_..._has_identity 对齐: 至少有食材或文本名
        if self.ingredient_id is None and self.item_name is None:
            raise ValueError("需提供 ingredient_id 或 item_name")
        return self


class ShoppingItemPurchase(BaseModel):
    """打勾购买。入库项需填实际购买量(→ I9 回流)。"""
    purchased_amount: Decimal | None = Field(default=None, gt=0)
    purchased_unit: str = Field(default="g", max_length=20)


class PreviewItem(BaseModel):
    """库存预扣视图一行(I6): 实际 / 需求 / 预计剩余(可负)。"""
    ingredient_id: int
    actual_grams: Decimal
    demand_grams: Decimal
    projected_remaining_grams: Decimal   # 负 = 排的饭会缺这么多