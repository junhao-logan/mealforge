from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.meal_plans.models import MealPlan

if TYPE_CHECKING:  # 仅类型标注, 不产生运行时 import(避免耦合/环)
    from app.meal_plans.models import MealPlanEntry
    from app.recipes.models import RecipeIngredient

# 餐次自定义排序: 早 < 午 < 晚 < 加餐(字母序会让 dinner<lunch, 错)
MEAL_TYPE_ORDER = {"breakfast": 0, "lunch": 1, "dinner": 2, "snack": 3}


def meal_type_sort_key(meal_type: str) -> int:
    return MEAL_TYPE_ORDER.get(meal_type, 99)


def line_demand(ri: RecipeIngredient, entry: MealPlanEntry) -> Decimal:
    """一餐一味的需求量(克, I13) = 配方用量 × 这一餐的份数倍率。

    I13 简化: 直接乘 entry.servings(配方倍数), 不除 variant.servings。
    这是"库存扣减(deduct_for_entry)"与"缺口计算(compute_shortfall)"的
    共享公式 —— I13 语义的单一真相源。Phase 3 batch-cooking 拆分
    "做几份 vs 吃几份"时, 变化只落在这里。
    """
    return ri.quantity_grams * entry.servings


async def get_or_create_default_plan(db: AsyncSession, user_id) -> MealPlan:
    """取用户的 default plan, 没有就建一个(quick-log 用)。
    default plan: plan_type='default', 首建时 start=end=今天, 后续动态撑大。
    """
    plan = (await db.execute(
        select(MealPlan).where(
            MealPlan.user_id == user_id,
            MealPlan.plan_type == "default",
        )
    )).scalar_one_or_none()

    if plan is None:
        today = date.today()
        plan = MealPlan(
            user_id=user_id, name="My Log", plan_type="default",
            start_date=today, end_date=today, is_template=False,
        )
        db.add(plan)
        await db.flush()  # flush 拿到 plan.id, 但不 commit(让调用方统一提交)
    return plan


def expand_plan_range(plan: MealPlan, d: date) -> None:
    """动态撑大: 若日期 d 超出 plan 范围, 撑大 start/end 容纳它。"""
    if d < plan.start_date:
        plan.start_date = d
    if d > plan.end_date:
        plan.end_date = d