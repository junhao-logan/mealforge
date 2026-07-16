# app/inventory/schemas.py
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InventoryItemCreate(BaseModel):
    """入库一个批次。Week 5: 输入即克(input_unit 暂固定 g),换算 Week 6 接。"""
    ingredient_id: int
    # 用户填的量。Week 5 语义 = 克数;Week 6 起可为"2 个"再经 grams_per_unit 换算
    input_amount: Decimal = Field(gt=0)
    input_unit: str = Field(default="g", max_length=20)
    purchased_at: date | None = None
    expires_at: date | None = None


class InventoryItemUpdate(BaseModel):
    """改批次。全部可选,只改传入的字段。"""
    input_amount: Decimal | None = Field(default=None, gt=0)
    input_unit: str | None = Field(default=None, max_length=20)
    purchased_at: date | None = None
    expires_at: date | None = None


class InventoryItemRead(BaseModel):
    """返回给前端。含 DB 生成字段 + I4 临期状态(查询时算,非存储)。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    ingredient_id: int
    quantity_grams: Decimal
    input_amount: Decimal
    input_unit: str
    purchased_at: date | None
    expires_at: date | None
    # I4: 'expiring'(未来 N 天内过期) / None(不临期或无过期日)。查询时算,不落库。
    expiry_status: str | None = None
    created_at: datetime
    updated_at: datetime