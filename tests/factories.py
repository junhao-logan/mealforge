# tests/factories.py
"""测试种子 helper —— 各测试共用。均 flush(不 commit), 由事务回滚清理。"""
from datetime import date, timedelta
from decimal import Decimal

from app.ingredients.models import Ingredient
from app.inventory.models import InventoryItem
from app.meal_plans.models import MealPlan, MealPlanEntry
from app.recipes.models import Recipe, RecipeIngredient, RecipeVariant
from app.users.models import User

TODAY = date(2026, 6, 1)
WEEK_END = TODAY + timedelta(days=6)


async def make_user(db, clerk="u_main") -> User:
    u = User(clerk_user_id=clerk)
    db.add(u)
    await db.flush()
    return u


async def make_ingredient(db, name) -> Ingredient:
    ing = Ingredient(name=name, name_normalized=name)
    db.add(ing)
    await db.flush()
    return ing


async def make_variant(db, *lines) -> RecipeVariant:
    """lines: (ingredient, grams) 元组; 建 recipe + variant + 配料。"""
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


async def make_plan(db, user, start=TODAY, end=WEEK_END) -> MealPlan:
    p = MealPlan(user_id=user.id, start_date=start, end_date=end)
    db.add(p)
    await db.flush()
    return p


async def make_entry(db, plan, variant, servings, day=TODAY, completed=False) -> MealPlanEntry:
    e = MealPlanEntry(
        meal_plan_id=plan.id, scheduled_date=day, meal_type="dinner",
        recipe_variant_id=variant.id, servings=Decimal(str(servings)),
        is_completed=completed,
    )
    db.add(e)
    await db.flush()
    return e


async def make_stock(db, user, ing, grams) -> InventoryItem:
    it = InventoryItem(
        user_id=user.id, ingredient_id=ing.id,
        quantity_grams=Decimal(str(grams)),
        input_amount=Decimal(str(grams)), input_unit="g",
    )
    db.add(it)
    await db.flush()
    return it


async def make_shopping_list(db, user, start=TODAY, end=WEEK_END):
    from app.shopping.models import ShoppingList
    sl = ShoppingList(user_id=user.id, forecast_start=start, forecast_end=end, status="active")
    db.add(sl)
    await db.flush()
    return sl


async def make_shopping_item(
    db, sl, *, ingredient=None, item_name=None, source="auto",
    needed_grams=None, add_to_inventory=True,
):
    from decimal import Decimal as _D
    from app.shopping.models import ShoppingListItem
    item = ShoppingListItem(
        shopping_list_id=sl.id,
        ingredient_id=(ingredient.id if ingredient else None),
        item_name=item_name,
        source=source,
        needed_grams=(_D(str(needed_grams)) if needed_grams is not None else None),
        add_to_inventory=add_to_inventory,
    )
    db.add(item)
    await db.flush()
    return item