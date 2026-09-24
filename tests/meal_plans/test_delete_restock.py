# tests/meal_plans/test_delete_restock.py
"""A5 删除餐次 / 计划时可选退回库存; 退不回去的部分提示。A6 零数量批次默认隐藏。"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.inventory.models import InventoryItem, InventoryTransaction
from app.inventory.services import deduct_for_entry, restock_for_entry
from tests.factories import (
    make_entry,
    make_ingredient,
    make_plan,
    make_stock,
    make_user,
    make_variant,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

FUTURE = date.today() + timedelta(days=10)


async def _completed_meal(db, user, ing, grams, stock_grams=100, plan=None):
    """建库存 + 一顿已完成(已扣库存)的饭, 返回 (plan, entry, batch)。"""
    batch = await make_stock(db, user, ing, stock_grams, expires_at=FUTURE)
    v = await make_variant(db, (ing, grams))
    today = date.today()
    p = plan or await make_plan(db, user, start=today, end=today + timedelta(days=6))
    e = await make_entry(db, p, v, servings=1, day=today)
    await deduct_for_entry(db, user.id, e)
    e.is_completed = True
    await db.flush()
    return p, e, batch


# ---------- restock_for_entry: 退不回去的部分 ----------

async def test_restock_reports_deleted_batch_and_nets_out(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    _, e, batch = await _completed_meal(db, u, egg, 60)
    await db.delete(batch)                    # 用户手动删了原批次
    await db.flush()
    await db.refresh(e)

    lost = await restock_for_entry(db, u.id, e)
    assert lost == [{"ingredient_id": egg.id, "amount": Decimal("60")}]

    # 冲销流水让净额归零 → 再退一次不会重复报
    assert await restock_for_entry(db, u.id, e) == []
    reasons = (await db.execute(
        select(InventoryTransaction.reason).where(InventoryTransaction.source_entry_id == e.id)
    )).scalars().all()
    assert "reversal_lost" in reasons


async def test_restock_returns_nothing_when_all_restored(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    _, e, batch = await _completed_meal(db, u, egg, 100, stock_grams=100)
    assert batch.quantity_grams == Decimal("0")      # 扣光, 批次保留(A6)

    assert await restock_for_entry(db, u.id, e) == []
    assert batch.quantity_grams == Decimal("100")    # 退回原批次


# ---------- HTTP: 删除餐次 ----------

async def test_delete_completed_entry_with_restock(api_client):
    client, session, user = api_client
    egg = await make_ingredient(session, "egg_del1")
    p, e, batch = await _completed_meal(session, user, egg, 60)

    r = await client.delete(f"/meal-plans/{p.id}/entries/{e.id}?restock=true")

    assert r.status_code == 200, r.text
    assert r.json() == {"unrestorable": []}
    await session.refresh(batch)
    assert batch.quantity_grams == Decimal("100")


async def test_delete_completed_entry_without_restock_keeps_consumption(api_client):
    client, session, user = api_client
    egg = await make_ingredient(session, "egg_del2")
    p, e, batch = await _completed_meal(session, user, egg, 60)

    r = await client.delete(f"/meal-plans/{p.id}/entries/{e.id}")

    assert r.status_code == 200
    await session.refresh(batch)
    assert batch.quantity_grams == Decimal("40")


async def test_delete_reports_unrestorable_with_name(api_client):
    client, session, user = api_client
    egg = await make_ingredient(session, "egg_del3")
    p, e, batch = await _completed_meal(session, user, egg, 60)
    await session.delete(batch)
    await session.flush()

    r = await client.delete(f"/meal-plans/{p.id}/entries/{e.id}?restock=true")

    assert r.status_code == 200
    [loss] = r.json()["unrestorable"]
    assert loss["name"] == "egg_del3" and loss["unit"] == "g"
    assert Decimal(loss["amount"]) == Decimal("60")


async def test_restock_flag_ignored_for_uncompleted_entry(api_client):
    client, session, user = api_client
    egg = await make_ingredient(session, "egg_del4")
    batch = await make_stock(session, user, egg, 100, expires_at=FUTURE)
    v = await make_variant(session, (egg, 60))
    today = date.today()
    p = await make_plan(session, user, start=today, end=today)
    e = await make_entry(session, p, v, servings=1, day=today)

    r = await client.delete(f"/meal-plans/{p.id}/entries/{e.id}?restock=true")

    assert r.status_code == 200
    await session.refresh(batch)
    assert batch.quantity_grams == Decimal("100")    # 没扣过, 也不会多加


# ---------- HTTP: 删除计划 ----------

async def test_delete_plan_restocks_all_completed(api_client):
    client, session, user = api_client
    egg = await make_ingredient(session, "egg_plan1")
    rice = await make_ingredient(session, "rice_plan1")
    p, _, egg_batch = await _completed_meal(session, user, egg, 30)
    _, _, rice_batch = await _completed_meal(session, user, rice, 50, plan=p)

    r = await client.delete(f"/meal-plans/{p.id}?restock=true")

    assert r.status_code == 200
    await session.refresh(egg_batch)
    await session.refresh(rice_batch)
    assert egg_batch.quantity_grams == Decimal("100")
    assert rice_batch.quantity_grams == Decimal("100")


async def test_delete_plan_without_restock(api_client):
    client, session, user = api_client
    egg = await make_ingredient(session, "egg_plan2")
    p, _, batch = await _completed_meal(session, user, egg, 30)

    r = await client.delete(f"/meal-plans/{p.id}")

    assert r.status_code == 200
    await session.refresh(batch)
    assert batch.quantity_grams == Decimal("70")


# ---------- HTTP: 撤销完成带提示 ----------

async def test_uncomplete_returns_entry_and_unrestorable(api_client):
    client, session, user = api_client
    egg = await make_ingredient(session, "egg_un1")
    p, e, batch = await _completed_meal(session, user, egg, 60)
    await session.delete(batch)
    await session.flush()

    r = await client.patch(f"/meal-plans/{p.id}/entries/{e.id}/uncomplete")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["entry"]["is_completed"] is False
    assert body["unrestorable"][0]["name"] == "egg_un1"


# ---------- A6: 零数量批次默认隐藏 ----------

async def test_inventory_list_hides_empty_batches(api_client):
    client, session, user = api_client
    egg = await make_ingredient(session, "egg_empty")
    empty = await make_stock(session, user, egg, 0, expires_at=FUTURE)
    full = await make_stock(session, user, egg, 50, expires_at=FUTURE)

    ids = [x["id"] for x in (await client.get("/inventory")).json()]
    assert full.id in ids and empty.id not in ids

    ids = [x["id"] for x in (await client.get("/inventory?include_empty=true")).json()]
    assert empty.id in ids
    assert (await session.get(InventoryItem, empty.id)) is not None   # 数据库里还在
