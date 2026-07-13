# app/inventory/models.py
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InventoryItem(Base):
    """库存批次 —— 一食材可多行(不同批次/过期日)。FEFO 扣减按 expires_at 排序。"""
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # user_id UUID 对齐真实 users.id(identity shadow); 删用户带走库存
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # 库存引用的食材不准删 → RESTRICT(保护库存不悬空)
    ingredient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingredients.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # 克本位(I3): 计算唯一来源; 扣减/求和都用它
    quantity_grams: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # D5=B 双表示: 用户原始输入(展示/还原用), 与 recipe_ingredients 一致
    input_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    input_unit: Mapped[str] = mapped_column(String(20), nullable=False)

    purchased_at: Mapped[date | None] = mapped_column(Date)
    # FEFO 排序键; NULL = 无过期日(排最后, 不提醒)
    expires_at: Mapped[date | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        # 按食材取批次 + FEFO 排序的高频查询
        Index(
            "idx_inventory_items_user_ingredient_expires",
            "user_id", "ingredient_id", "expires_at",
        ),
    )


class InventoryTransaction(Base):
    """库存变动流水 —— append-only 审计日志(I2)。当前库存不靠它算; 保留 90 天。"""
    __tablename__ = "inventory_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    ingredient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingredients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # 关联具体批次; 批次被删/扣光后置空但流水留存 → SET NULL
    inventory_item_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("inventory_items.id", ondelete="SET NULL")
    )

    # +入库 / -扣减 (克本位)
    delta_grams: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # purchase / meal_consumption / adjustment / waste
    reason: Mapped[str] = mapped_column(String(20), nullable=False)
    # 哪次完成餐次导致的扣减; entry 删了流水仍在 → SET NULL
    source_entry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("meal_plan_entries.id", ondelete="SET NULL")
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "idx_inventory_transactions_user_ingredient_time",
            "user_id", "ingredient_id", "occurred_at",
        ),
        Index("idx_inventory_transactions_source_entry", "source_entry_id"),
        # 支撑按时间清理旧流水(90天保留策略)
        Index("idx_inventory_transactions_occurred", "occurred_at"),
    )