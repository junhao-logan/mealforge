# tests/shopping/test_compute_shortfall.py
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

from app.ingredients.models import Ingredient
from app.inventory.models import InventoryItem
from app.meal_plans.models import MealPlan, MealPlanEntry
from app.recipes.models import Recipe, RecipeIngredient, RecipeVariant
from app.shopping.services import compute_shortfall
from app.users.models import User

TODAY = date(2026, 6, 1)
WEEK_END = TODAY + timedelta(days=6)

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── 种子 helper(flush 拿 id, 不 commit) ──
async def _user(db, clerk="u_main") -> User:
    u = User(clerk_user_id=clerk)
    db.add(u)
    await db.flush()
    return u


async def _ingredient(db, name) -> Ingredient:
    ing = Ingredient(name=name, name_normalized=name)
    db.add(ing)
    await db.flush()
    return ing


async def _variant(db, *lines) -> RecipeVariant:
    """lines: (ingredient, grams) 元组。建 recipe + variant + 配料。"""
    r = Recipe(name="r", source="user")
    db.add(r)
    await db.flush()
    v = RecipeVariant(recipe_id=r.id, name="std", instructions="x")
    db.add(v)
    await db.flush()
    for ing, grams in lines:
        db.add(RecipeIngredient(
            recipe_variant_id=v.id, ingredient_id=ing.id,
            quantity_grams=Decimal(str(grams)),
            input_amount=Decimal(str(grams)), input_unit="g",
        ))
    await db.flush()
    return v


async def _plan(db, user) -> MealPlan:
    p = MealPlan(user_id=user.id, start_date=TODAY, end_date=WEEK_END)
    db.add(p)
    await db.flush()
    return p


async def _entry(db, plan, variant, servings, day=TODAY, completed=False) -> MealPlanEntry:
    e = MealPlanEntry(
        meal_plan_id=plan.id, scheduled_date=day, meal_type="dinner",
        recipe_variant_id=variant.id, servings=Decimal(str(servings)),
        is_completed=completed,
    )
    db.add(e)
    await db.flush()
    return e


async def _stock(db, user, ing, grams) -> InventoryItem:
    it = InventoryItem(
        user_id=user.id, ingredient_id=ing.id,
        quantity_grams=Decimal(str(grams)),
        input_amount=Decimal(str(grams)), input_unit="g",
    )
    db.add(it)
    await db.flush()
    return it


def _gap(result, ingredient_id):
    for r in result:
        if r["ingredient_id"] == ingredient_id:
            return r["shortfall_grams"]
    return None


# ── 场景 ──
async def test_basic_shortfall(db):
    """需求 > 库存 → 返回差额。"""
    u = await _user(db)
    tomato = await _ingredient(db, "tomato")
    v = await _variant(db, (tomato, 200))
    p = await _plan(db, u)
    await _entry(db, p, v, servings=2)          # 需求 400
    await _stock(db, u, tomato, 250)            # 库存 250
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert _gap(out, tomato.id) == Decimal("150.00")


async def test_enough_stock_excluded(db):
    """库存 ≥ 需求 → 不出现在缺口里。"""
    u = await _user(db)
    tomato = await _ingredient(db, "tomato")
    v = await _variant(db, (tomato, 200))
    p = await _plan(db, u)
    await _entry(db, p, v, servings=1)          # 需求 200
    await _stock(db, u, tomato, 500)            # 库存充足
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert _gap(out, tomato.id) is None


async def test_completed_entry_not_counted(db):
    """已完成 entry 不计入需求(双重计数护栏)。"""
    u = await _user(db)
    tomato = await _ingredient(db, "tomato")
    v = await _variant(db, (tomato, 200))
    p = await _plan(db, u)
    await _entry(db, p, v, servings=2, completed=True)   # 已完成 → 不算
    # 无库存, 若误算会缺 400
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert out == []


async def test_past_dated_entry_excluded(db):
    """scheduled_date < 窗口起点 的漏做餐不进采购(D2)。"""
    u = await _user(db)
    tomato = await _ingredient(db, "tomato")
    v = await _variant(db, (tomato, 200))
    p = await _plan(db, u)
    await _entry(db, p, v, servings=2, day=TODAY - timedelta(days=3))  # 过去
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert out == []


async def test_same_variant_multiple_entries_accumulate(db):
    """同一 variant 多餐: 份数累加(2 + 1.5 = 3.5×)。"""
    u = await _user(db)
    tomato = await _ingredient(db, "tomato")
    v = await _variant(db, (tomato, 200))
    p = await _plan(db, u)
    await _entry(db, p, v, servings=2, day=TODAY)
    await _entry(db, p, v, servings=Decimal("1.5"), day=TODAY + timedelta(days=1))
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert _gap(out, tomato.id) == Decimal("700.00")   # 200*3.5


async def test_multi_ingredient_aggregation(db):
    """一餐多味, 各食材独立聚合。"""
    u = await _user(db)
    tomato = await _ingredient(db, "tomato")
    egg = await _ingredient(db, "egg")
    v = await _variant(db, (tomato, 200), (egg, 120))
    p = await _plan(db, u)
    await _entry(db, p, v, servings=2)
    await _stock(db, u, tomato, 100)
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert _gap(out, tomato.id) == Decimal("300.00")   # 400-100
    assert _gap(out, egg.id) == Decimal("240.00")      # 240-0


async def test_empty_window_returns_empty(db):
    """窗口内无未完成 entry → []。"""
    u = await _user(db)
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert out == []


async def test_user_isolation(db):
    """别人的 entry/库存不串进来(JOIN 用户过滤)。"""
    u1 = await _user(db, "u1")
    u2 = await _user(db, "u2")
    tomato = await _ingredient(db, "tomato")
    v = await _variant(db, (tomato, 200))
    p2 = await _plan(db, u2)
    await _entry(db, p2, v, servings=5)         # u2 的餐
    await _stock(db, u2, tomato, 0)
    out = await compute_shortfall(db, u1.id, TODAY, WEEK_END)   # 查 u1
    assert out == []                            # u1 什么都没有


async def test_subcent_gap_not_emitted(db):
    """量化: 需求超库存不足 0.01g 时不生成微缺口。"""
    u = await _user(db)
    tomato = await _ingredient(db, "tomato")
    v = await _variant(db, (tomato, Decimal("100.25")))
    p = await _plan(db, u)
    await _entry(db, p, v, servings=Decimal("2.5"))   # 100.25*2.5 = 250.625
    await _stock(db, u, tomato, Decimal("250.62"))    # 差 0.005 → 量化后 0
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert _gap(out, tomato.id) is None