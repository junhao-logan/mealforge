# app/ingredients/models.py
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
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

    # 营养基准 (A2 单位本位): 上面 4 个营养字段表示"每 nutrition_basis_amount 个
    # nutrition_basis_unit 的营养"。nutrition_basis_unit 即该食材的【规范单位】——
    # 库存量 / 配方量 / 扣减都以它衡量。
    #   · 库存/USDA/系统食材 = (100, 'g'): 与旧 per-100g 语义完全一致, 无行为变化。
    #   · 用户自建"单位本位"食材 = 如 (1, '块'): 营养按"每 1 块"记, 数量也以"块"计, 不换算克。
    # 命名说明: quantity_grams / per_100g_* 沿用旧列名, 语义已泛化为"规范单位下的量/每基准营养";
    #   克是质量食材的规范单位, 故旧名对绝大多数食材仍准确(A2 取舍: 诚实营养基准 + 低迁移风险)。
    nutrition_basis_amount: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False, server_default=text("100")
    )
    nutrition_basis_unit: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'g'")
    )

    shelf_life_days: Mapped[int | None] = mapped_column(Integer)

    # 来源 (D1/D3)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'user'")
    )  # 'usda' / 'system' / 'user'
    usda_fdc_id: Mapped[str | None] = mapped_column(String(20))  # seed upsert key
    # 归属(I11): UUID FK->users, 删用户置空不销毁食材(SET NULL)。usda/system 为 NULL
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    # 可见性(I11): 'private'(默认) / 'global'。与 source 正交(source=哪来的, visibility=谁能看)
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'private'")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    @property
    def allowed_units(self) -> list[str]:
        """该食材在库存/菜谱里可选的单位。
        · 质量食材(规范单位 g/ml): [展示单位(如 piece), 规范单位] —— 库存/审核食材可用克。
        · 单位本位食材(规范单位为 块/个 等): 只可选它自己的单位, 不给克。
        兜底: 未从 DB 刷新时 nutrition_basis_unit 可能为 None, 视为 'g'。
        """
        canonical = self.nutrition_basis_unit or "g"
        if canonical in ("g", "ml") and self.default_unit and self.default_unit != canonical:
            return [self.default_unit, canonical]
        return [canonical]

    __table_args__ = (
        Index("idx_ingredients_name_normalized", "name_normalized"),
        Index("idx_ingredients_category", "category"),
        Index("idx_ingredients_source", "source"),
        Index("idx_ingredients_created_by", "created_by_user_id"),
        Index(
            "idx_ingredients_usda_fdc_id",
            "usda_fdc_id",
            unique=True,
            postgresql_where=text("usda_fdc_id IS NOT NULL"),
        ),
    )