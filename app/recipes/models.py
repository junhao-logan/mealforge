from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.ingredients.models import Ingredient


class Recipe(Base):
    """菜谱概念层 —— 一道菜的身份(如'宫保鸡丁'),具体做法在 RecipeVariant。"""
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    cuisine: Mapped[str | None] = mapped_column(String(50))  # chinese/western/japanese...

    # 来源追溯
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # system/user/ai_generated
    # ⚠️ created_by_user_id / ai_generation_log_id: 留列不加 FK
    #   - users.id 是 UUID, 这里 BIGINT, 类型不匹配(同 ingredients 的处理)
    #   - ai_generation_logs 表尚未建立
    #   待类型对齐 / 目标表建好后再补 FK
    created_by_user_id: Mapped[int | None] = mapped_column(BigInteger)
    ai_generation_log_id: Mapped[int | None] = mapped_column(BigInteger)

    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )

    # 一个 Recipe 至少有一个 Variant; 删 Recipe 级联删其所有 Variant
    variants: Mapped[list[RecipeVariant]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_recipes_created_by", "created_by_user_id"),
        Index("idx_recipes_source", "source"),
        Index("idx_recipes_name", "name"),
    )


class RecipeVariant(Base):
    """做法层 —— 同一道菜的不同版本(经典/减脂/增肌)。营养缓存在这一层。"""
    __tablename__ = "recipe_variants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 这个 FK 能加: recipes 表本次同时建立, 类型都是 BIGINT
    recipe_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 系统级固定枚举(产品定义); 个性化标签走 recipe_variant_tags(本期未建)
    purpose_tag: Mapped[str] = mapped_column(
        String(30), nullable=False, default="default"
    )  # default/fat_loss/muscle_gain/stomach_friendly/low_carb/high_protein
    extra_notes: Mapped[str | None] = mapped_column(Text)

    instructions: Mapped[str] = mapped_column(Text, nullable=False)  # MVP 纯文本
    cooking_time_minutes: Mapped[int | None] = mapped_column(Integer)
    difficulty: Mapped[str | None] = mapped_column(String(20))  # easy/medium/hard
    servings: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # 营养缓存(由 recipe_ingredients 聚合, D6 service 写入)
    # 全 nullable: 配料未填 / 含 unknown 营养时为 NULL(D2 语义延续到聚合层)
    total_calories: Mapped[Decimal | None] = mapped_column(Numeric(7, 1))
    total_protein_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    total_carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    total_fat_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    total_grams: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    nutrition_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )

    recipe: Mapped[Recipe] = relationship(back_populates="variants")
    ingredients: Mapped[list[RecipeIngredient]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_recipe_variants_recipe_id", "recipe_id"),
        Index("idx_recipe_variants_purpose_tag", "purpose_tag"),
    )


class RecipeIngredient(Base):
    """配料层 —— 某个 Variant 用了哪些食材、各多少。
    D5=B: 存归一化克数(供 O(1) 营养聚合) + 用户原始输入(供友好显示)。
    """
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    recipe_variant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("recipe_variants.id", ondelete="CASCADE"), nullable=False
    )
    # 这个 FK 能加: ingredients 表已存在, 都是 BIGINT
    ingredient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False
    )

    # 归一化克数: 写入时 input_amount × grams_per_unit 算好, 营养聚合直接用(D5)
    quantity_grams: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    # 用户原始输入: 显示用(D5=B), 读取时还原"2 个"而非"100g"
    input_amount: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    input_unit: Mapped[str] = mapped_column(String(20), nullable=False)  # 'g' 或食材的 default_unit

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    variant: Mapped[RecipeVariant] = relationship(back_populates="ingredients")
    # 指向食材, 供营养聚合读 per-100g + 读取时拿食材名
    ingredient: Mapped["Ingredient"] = relationship()

    __table_args__ = (
        Index("idx_recipe_ingredients_variant_id", "recipe_variant_id"),
        Index("idx_recipe_ingredients_ingredient_id", "ingredient_id"),
    )