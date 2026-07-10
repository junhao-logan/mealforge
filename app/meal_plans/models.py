from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.recipes.models import RecipeVariant

class MealPlan(Base):
    """餐食计划聚合根 —— 任意起止日期,允许同用户多个计划时间重叠。"""
    __tablename__ = "meal_plans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # user_id 用 UUID 对齐真实 users.id(identity shadow); 删用户带走计划
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str | None] = mapped_column(String(100))  # NULL = 自动命名
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    plan_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="regular"
    )  # regular / template / special
    is_template: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ai_generation_log_id: 留列不加 FK(ai_generation_logs 表未建, 同 recipes)
    ai_generation_log_id: Mapped[int | None] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )

    # 一个 plan 包含多个 entry; 删 plan 级联删其所有 entry
    entries: Mapped[list[MealPlanEntry]] = relationship(
        back_populates="meal_plan", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # end_date >= start_date, DB 层兜底(应用层也会校验)
        CheckConstraint("end_date >= start_date", name="chk_date_range"),
        Index("idx_meal_plans_user_dates", "user_id", "start_date", "end_date"),
        # partial index: 只为模板建索引(查"我的模板"的高频小集合)
        Index(
            "idx_meal_plans_template", "user_id", "is_template",
            postgresql_where=(is_template == True),  # noqa: E712
        ),
    )


class MealPlanEntry(Base):
    """计划中的每一餐 —— 指向 RecipeVariant(具体做法), 不是 Recipe。"""
    __tablename__ = "meal_plan_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 依附于 plan, 删 plan 带走 → CASCADE
    meal_plan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False
    )

    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # breakfast / lunch / dinner / snack
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 同餐次内多条排序(早餐吃两样 / 多个加餐)

    # 排进计划的菜谱版本不准被删 → RESTRICT(保护计划不悬空)
    recipe_variant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("recipe_variants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    servings: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("1.0")
    )  # 这一餐吃几份(算营养时 variant 营养 × servings)

    # MVP: is_completed 替代独立 meal_logs 表(Phase 2 演化)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )

    meal_plan: Mapped[MealPlan] = relationship(back_populates="entries")
    # 指向菜谱版本, 供读取时拿营养/名字(纯导航, FK 列已存在)
    recipe_variant: Mapped["RecipeVariant"] = relationship()

    __table_args__ = (
        Index("idx_meal_plan_entries_plan_date", "meal_plan_id", "scheduled_date"),
        Index("idx_meal_plan_entries_variant", "recipe_variant_id"),
        Index("idx_meal_plan_entries_completed", "meal_plan_id", "is_completed"),
    )