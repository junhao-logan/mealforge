# tests/meal_plans/test_plan_helpers.py
"""meal_plans/services.py 辅助函数: 餐次排序 / 默认计划 / 动态撑大范围。

注意: 本文件混了同步纯函数测试和异步 DB 测试。
- 同步测试(纯函数): 不加 asyncio 标记
- 异步测试(需 db): 单独加 @pytest.mark.asyncio(loop_scope="session"),
  必须与 db fixture 同一事件循环, 否则 asyncpg 报 "attached to a different loop"
"""
from datetime import date

import pytest
from sqlalchemy import func, select

from app.meal_plans.models import MealPlan
from app.meal_plans.services import (
    expand_plan_range,
    get_or_create_default_plan,
    meal_type_sort_key,
)
from tests.factories import make_plan, make_user

# 只给异步 DB 测试用的标记(同步纯函数测试不加)
_db_test = pytest.mark.asyncio(loop_scope="session")


# ---- meal_type_sort_key(纯函数, 同步) ----

def test_meal_type_order_is_chronological():
    """早<午<晚<加餐(字母序会让 dinner<lunch, 故需自定义)。"""
    order = ["breakfast", "lunch", "dinner", "snack"]
    keys = [meal_type_sort_key(m) for m in order]
    assert keys == sorted(keys)                 # 顺序单调递增
    assert meal_type_sort_key("dinner") > meal_type_sort_key("lunch")


def test_unknown_meal_type_sorts_last():
    """未知餐段排最后(99)。"""
    assert meal_type_sort_key("brunch") == 99


# ---- get_or_create_default_plan(async, 需 DB) ----

@_db_test
async def test_creates_default_plan_when_none(db):
    """用户无 default plan → 建一个(plan_type=default)。"""
    u = await make_user(db)
    plan = await get_or_create_default_plan(db, u.id)

    assert plan.plan_type == "default"
    assert plan.user_id == u.id
    n = (await db.execute(
        select(func.count()).select_from(MealPlan).where(
            MealPlan.user_id == u.id, MealPlan.plan_type == "default")
    )).scalar()
    assert n == 1


@_db_test
async def test_returns_existing_default_plan(db):
    """已有 default plan → 返回同一个, 不重复建。"""
    u = await make_user(db)
    first = await get_or_create_default_plan(db, u.id)
    second = await get_or_create_default_plan(db, u.id)

    assert first.id == second.id
    n = (await db.execute(
        select(func.count()).select_from(MealPlan).where(
            MealPlan.user_id == u.id, MealPlan.plan_type == "default")
    )).scalar()
    assert n == 1


# ---- expand_plan_range(改对象; 因需 make_plan 落库故走 db) ----

@_db_test
async def test_expand_grows_end_for_future_date(db):
    """日期晚于 end → 撑大 end。"""
    u = await make_user(db)
    plan = await make_plan(db, u, start=date(2026, 1, 10), end=date(2026, 1, 15))
    expand_plan_range(plan, date(2026, 1, 20))
    assert plan.end_date == date(2026, 1, 20)
    assert plan.start_date == date(2026, 1, 10)


@_db_test
async def test_expand_grows_start_for_past_date(db):
    """日期早于 start → 撑大 start。"""
    u = await make_user(db)
    plan = await make_plan(db, u, start=date(2026, 1, 10), end=date(2026, 1, 15))
    expand_plan_range(plan, date(2026, 1, 5))
    assert plan.start_date == date(2026, 1, 5)
    assert plan.end_date == date(2026, 1, 15)


@_db_test
async def test_expand_noop_when_inside_range(db):
    """日期在范围内 → 不变。"""
    u = await make_user(db)
    plan = await make_plan(db, u, start=date(2026, 1, 10), end=date(2026, 1, 15))
    expand_plan_range(plan, date(2026, 1, 12))
    assert plan.start_date == date(2026, 1, 10)
    assert plan.end_date == date(2026, 1, 15)