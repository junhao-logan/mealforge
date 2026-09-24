# tests/shopping/test_in_flight.py
"""A8 采购去重: 在途量(所有进行中清单里未购的入库项)先从缺口里扣掉。"""
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.inventory.models import InventoryItem
from app.shopping.models import ShoppingListItem
from app.shopping.schemas import ShoppingItemCreate
from app.shopping.services import (
    add_manual_item,
    close_sibling_items,
    compute_preview,
    generate_shopping_list,
    in_flight_by_ingredient,
    mark_item_purchased,
    regenerate_auto_items,
)
from tests.factories import (
    TODAY,
    WEEK_END,
    make_entry,
    make_ingredient,
    make_plan,
    make_shopping_list,
    make_user,
    make_variant,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _need(db, grams=60, name="egg"):
    """一个用户 + 一顿今天要吃的饭, 需要 grams 的某食材, 库存为 0。"""
    u = await make_user(db)
    ing = await make_ingredient(db, name)
    v = await make_variant(db, (ing, grams))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=1, day=TODAY)
    return u, ing


async def _items(db, sl, ing=None):
    stmt = select(ShoppingListItem).where(ShoppingListItem.shopping_list_id == sl.id)
    if ing is not None:
        stmt = stmt.where(ShoppingListItem.ingredient_id == ing.id)
    return list((await db.execute(stmt.order_by(ShoppingListItem.id))).scalars().all())


def _manual(ing, grams):
    return ShoppingItemCreate(ingredient_id=ing.id, needed_grams=Decimal(str(grams)))


# ---------- 跨清单 / 同清单扣在途量 ----------

async def test_second_list_does_not_duplicate(db):
    u, egg = await _need(db, 60)
    a = await generate_shopping_list(db, u.id, TODAY, WEEK_END, today=TODAY)
    b = await generate_shopping_list(db, u.id, TODAY, WEEK_END, today=TODAY)

    assert [i.needed_grams for i in await _items(db, a, egg)] == [Decimal("60.00")]
    assert await _items(db, b, egg) == []            # 已在 A 里等着买了


async def test_second_list_only_adds_the_rest(db):
    u, egg = await _need(db, 60)
    a = await make_shopping_list(db, u)
    await add_manual_item(db, a, _manual(egg, 20))

    b = await generate_shopping_list(db, u.id, TODAY, WEEK_END, today=TODAY)

    [auto] = await _items(db, b, egg)
    assert auto.source == "auto" and auto.needed_grams == Decimal("40.00")


async def test_regenerate_subtracts_own_manual(db):
    u, egg = await _need(db, 60)
    sl = await generate_shopping_list(db, u.id, TODAY, WEEK_END, today=TODAY)
    await add_manual_item(db, sl, _manual(egg, 20))

    await regenerate_auto_items(db, sl, today=TODAY)

    rows = {(i.source, i.needed_grams) for i in await _items(db, sl, egg)}
    assert rows == {("manual", Decimal("20")), ("auto", Decimal("40.00"))}


async def test_purchased_items_are_not_in_flight(db):
    u, egg = await _need(db, 60)
    sl = await make_shopping_list(db, u)
    item = await add_manual_item(db, sl, _manual(egg, 60))
    assert (await in_flight_by_ingredient(db, u.id))[egg.id] == Decimal("60")

    await mark_item_purchased(db, item, u.id, purchased_amount=Decimal("60"), today=TODAY)

    assert egg.id not in await in_flight_by_ingredient(db, u.id)


async def test_text_only_and_non_inventory_items_ignored(db):
    u, egg = await _need(db, 60)
    sl = await make_shopping_list(db, u)
    await add_manual_item(db, sl, ShoppingItemCreate(item_name="kitchen paper"))
    await add_manual_item(db, sl, ShoppingItemCreate(
        ingredient_id=egg.id, needed_grams=Decimal("30"), add_to_inventory=False))

    assert await in_flight_by_ingredient(db, u.id) == {}


# ---------- 缺口预览 ----------

async def test_preview_shows_in_list_and_to_add(db):
    u, egg = await _need(db, 60)
    sl = await make_shopping_list(db, u)
    await add_manual_item(db, sl, _manual(egg, 25))

    [row] = await compute_preview(db, u.id, TODAY, WEEK_END, today=TODAY)

    assert row["name"] == "egg" and row["unit"] == "g"
    assert row["in_list_grams"] == Decimal("25")
    assert row["to_add_grams"] == Decimal("35.00")


async def test_preview_to_add_never_negative(db):
    u, egg = await _need(db, 60)
    sl = await make_shopping_list(db, u)
    await add_manual_item(db, sl, _manual(egg, 100))

    [row] = await compute_preview(db, u.id, TODAY, WEEK_END, today=TODAY)

    assert row["to_add_grams"] == Decimal("0")


# ---------- 加入清单: 并入已有 manual ----------

async def test_add_merges_into_existing_manual(db):
    u, egg = await _need(db)
    sl = await make_shopping_list(db, u)
    first = await add_manual_item(db, sl, _manual(egg, 20))
    second = await add_manual_item(db, sl, _manual(egg, 15))

    assert second.id == first.id
    [row] = await _items(db, sl, egg)
    assert row.needed_grams == Decimal("35")


async def test_add_does_not_merge_into_auto(db):
    """auto 行重算时会被删, 并进去的量会丢 → 另起 manual 行(显示层再合并)。"""
    u, egg = await _need(db, 60)
    sl = await generate_shopping_list(db, u.id, TODAY, WEEK_END, today=TODAY)
    await add_manual_item(db, sl, _manual(egg, 10))

    assert sorted(i.source for i in await _items(db, sl, egg)) == ["auto", "manual"]


# ---------- 结算: 同食材兄弟行一起关 ----------

async def test_purchase_closes_siblings_single_batch(db):
    u, egg = await _need(db, 60)
    sl = await generate_shopping_list(db, u.id, TODAY, WEEK_END, today=TODAY)
    await add_manual_item(db, sl, _manual(egg, 10))
    auto, manual = await _items(db, sl, egg)

    await mark_item_purchased(db, auto, u.id, purchased_amount=Decimal("70"), today=TODAY)
    closed = await close_sibling_items(db, auto)

    assert closed == 1 and manual.is_purchased is True
    assert manual.purchased_amount is None           # 量只记在结算的那一行
    batches = (await db.execute(
        select(func.count()).select_from(InventoryItem).where(
            InventoryItem.user_id == u.id, InventoryItem.ingredient_id == egg.id)
    )).scalar_one()
    assert batches == 1                              # 只入库一次


# ---------- HTTP: 名字与单位 ----------

async def test_api_items_carry_name_and_unit(api_client):
    client, session, user = api_client
    tofu = await make_ingredient(session, "tofu_api")
    tofu.nutrition_basis_unit = "块"
    sl = await make_shopping_list(session, user)
    await session.flush()

    r = await client.post(f"/shopping-lists/{sl.id}/items",
                          json={"ingredient_id": tofu.id, "needed_grams": 2})
    assert r.status_code == 201, r.text
    assert r.json()["ingredient_name"] == "tofu_api" and r.json()["unit"] == "块"

    detail = (await client.get(f"/shopping-lists/{sl.id}")).json()
    assert detail["items"][0]["unit"] == "块"


async def test_api_unit_native_purchase(api_client):
    """按「块」计量的食材用自己的单位结算(以前前端写死 g 会被 422 拒绝)。"""
    client, session, user = api_client
    tofu = await make_ingredient(session, "tofu_buy")
    tofu.nutrition_basis_unit = "块"
    tofu.nutrition_basis_amount = Decimal("1")
    tofu.default_unit = "块"
    sl = await make_shopping_list(session, user)
    await session.flush()
    item = (await client.post(f"/shopping-lists/{sl.id}/items",
                              json={"ingredient_id": tofu.id, "needed_grams": 2})).json()

    r = await client.patch(f"/shopping-lists/{sl.id}/items/{item['id']}/purchase",
                           json={"purchased_amount": 2, "purchased_unit": "块"})

    assert r.status_code == 200, r.text
    assert r.json()["is_purchased"] is True
