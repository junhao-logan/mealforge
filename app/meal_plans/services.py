from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.meal_plans.models import MealPlan

# 餐次自定义排序: 早 < 午 < 晚 < 加餐(字母序会让 dinner<lunch, 错)
MEAL_TYPE_ORDER = {"breakfast": 0, "lunch": 1, "dinner": 2, "snack": 3}


def meal_type_sort_key(meal_type: str) -> int:
    return MEAL_TYPE_ORDER.get(meal_type, 99)


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