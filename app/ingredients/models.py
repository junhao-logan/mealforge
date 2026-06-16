# app/ingredients/models.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base  


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))

    # 营养 (per 100g) —— 全部 nullable: 0 ≠ unknown (D2)
    # energy: seed 按 1008→2048→2047 取值,单位锁 kcal
    per_100g_calories: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    per_100g_protein: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    per_100g_carbs: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    per_100g_fat: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # UI 单位元数据 (D4: 单 default_unit + grams_per_unit,多单位走 Phase 2)
    default_unit: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'g'")
    )
    grams_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(7, 2), nullable=False, server_default=text("1.0")
    )

    shelf_life_days: Mapped[int | None] = mapped_column(Integer)

    # 来源 (D1/D3)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'user'")
    )  # 'usda' / 'system' / 'user'
    usda_fdc_id: Mapped[str | None] = mapped_column(String(20))  # seed upsert key
    # created_by_user_id: 留列不加 FK(users.id 是 UUID,类型对不上,MVP 此列不写入)
    created_by_user_id: Mapped[int | None] = mapped_column(BigInteger)

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
        Index("idx_ingredients_name_normalized", "name_normalized"),
        Index("idx_ingredients_category", "category"),
        Index("idx_ingredients_source", "source"),
        Index(
            "idx_ingredients_usda_fdc_id",
            "usda_fdc_id",
            unique=True,
            postgresql_where=text("usda_fdc_id IS NOT NULL"),
        ),
    )