# tests/shopping/test_shopping_generation.py
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.shopping.models import ShoppingList, ShoppingListItem
from app.shopping.services import generate_shopping_list, regenerate_auto_items
from tests.factories import (
    TODAY, WEEK_END, make_entry, make_ingredient, make_plan,
    make_stock, make_user, make_variant,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _items(db, sl_id):
    return (await db.execute(
        select(ShoppingListItem)
        .where(ShoppingListItem.shopping_list_id == sl_id)
        .order_by(ShoppingListItem.id)
    )).scalars().all()


async def test_generate_materializes_shortfall(db):
    """生成: 缺口被物化成 auto 条目, 数量正确。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=2)          # 需求 400, 无库存
    sl = await generate_shopping_list(db, u.id, TODAY, WEEK_END, source_meal_plan_id=p.id)

    items = await _items(db, sl.id)
    assert len(items) == 1
    assert items[0].ingredient_id == tomato.id
    assert items[0].needed_grams == Decimal("400.00")
    assert items[0].source == "auto"
    assert items[0].is_purchased is False
    # 清单元数据快照
    assert sl.forecast_start == TODAY and sl.forecast_end == WEEK_END
    assert sl.source_meal_plan_id == p.id


async def test_generate_empty_when_no_shortfall(db):
    """无缺口: 仍建出清单(空), 供手动加项。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=1)          # 需求 200
    await make_stock(db, u, tomato, 500)            # 库存充足 → 无缺口
    sl = await generate_shopping_list(db, u.id, TODAY, WEEK_END)

    assert sl.id is not None                        # 清单存在
    assert await _items(db, sl.id) == []            # 但无条目


async def test_regenerate_keeps_purchased_auto(db):
    """重算: 已购 auto 条目保留(冻结的历史事实)。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=2)
    sl = await generate_shopping_list(db, u.id, TODAY, WEEK_END)

    # 标记已购 + 回流入库(库存补上 → 缺口消失)
    (await _items(db, sl.id))[0].is_purchased = True
    await make_stock(db, u, tomato, 400)
    await db.flush()

    await regenerate_auto_items(db, sl)
    items = await _items(db, sl.id)
    # 已购番茄仍在, 且没有因回流生成新的未购番茄
    assert len(items) == 1
    assert items[0].is_purchased is True
    assert items[0].ingredient_id == tomato.id


async def test_regenerate_keeps_manual(db):
    """重算: manual 条目一律保留。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=2)
    sl = await generate_shopping_list(db, u.id, TODAY, WEEK_END)

    db.add(ShoppingListItem(
        shopping_list_id=sl.id, item_name="厨房纸",
        source="manual", add_to_inventory=False,
    ))
    await db.flush()

    await regenerate_auto_items(db, sl)
    items = await _items(db, sl.id)
    assert any(i.source == "manual" and i.item_name == "厨房纸" for i in items)


async def test_regenerate_refreshes_unpurchased(db):
    """重算: 未购 auto 被删并按新缺口重插(份数变了 → 数量更新)。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p = await make_plan(db, u)
    e = await make_entry(db, p, v, servings=2)      # 需求 400
    sl = await generate_shopping_list(db, u.id, TODAY, WEEK_END)
    assert (await _items(db, sl.id))[0].needed_grams == Decimal("400.00")

    # 改份数 2 → 3, 重算
    e.servings = Decimal("3")
    await db.flush()
    await regenerate_auto_items(db, sl)

    items = await _items(db, sl.id)
    assert len(items) == 1                          # 旧的被删, 只留新的一条
    assert items[0].needed_grams == Decimal("600.00")
    assert items[0].source == "auto" and items[0].is_purchased is False