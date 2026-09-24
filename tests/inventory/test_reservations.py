# tests/inventory/test_reservations.py
"""A4 库存预留视图 + 手选批次 + 扣减一致性。

规则: 手选(硬预留, 可过期)优先 → 其余按餐次先后 FEFO, 且自动分配不碰过期批次。
真实扣减(deduct_for_entry)与预留视图同一规则 —— 显示什么就扣什么。
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.inventory.models import EntryBatchPick
from app.inventory.reservations import compute_reservations
from app.inventory.services import deduct_for_entry
from tests.factories import (
    make_entry,
    make_ingredient,
    make_plan,
    make_stock,
    make_user,
    make_variant,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

T = date(2026, 6, 1)                 # 模拟的"今天"
SOON = T + timedelta(days=3)         # 先过期
LATER = T + timedelta(days=10)       # 后过期
PAST = T - timedelta(days=1)         # 已过期


async def _meal(db, user, ing, grams, *, day=T, meal_type="dinner", plan=None, completed=False):
    v = await make_variant(db, (ing, grams))
    p = plan or await make_plan(
        db, user, start=day - timedelta(days=7), end=day + timedelta(days=7)
    )
    e = await make_entry(db, p, v, servings=1, day=day, completed=completed)
    e.meal_type = meal_type
    await db.flush()
    return e


async def _pick(db, entry, ing, *batches):
    for pos, b in enumerate(batches):
        db.add(EntryBatchPick(
            entry_id=entry.id, ingredient_id=ing.id, inventory_item_id=b.id, position=pos,
        ))
    await db.flush()


def _batch(res, b):
    return next(x for x in res["batches"] if x["batch_id"] == b.id)


def _line(res, entry):
    e = next(x for x in res["entries"] if x["entry_id"] == entry.id)
    return e["lines"][0]


# ---------- 自动分配(模拟 FEFO) ----------

async def test_single_meal_reserves_from_one_batch(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    b = await make_stock(db, u, egg, 100, expires_at=SOON)
    e = await _meal(db, u, egg, 60)

    res = await compute_reservations(db, u.id, today=T)

    rb = _batch(res, b)
    assert rb["reserved"] == Decimal("60") and rb["free"] == Decimal("40")
    assert rb["allocations"] == [{"entry_id": e.id, "amount": Decimal("60"), "manual": False}]
    assert res["shortfalls"] == []


async def test_meal_spans_batches_in_fefo_order(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    later = await make_stock(db, u, egg, 100, expires_at=LATER)
    soon = await make_stock(db, u, egg, 50, expires_at=SOON)
    e = await _meal(db, u, egg, 80)

    res = await compute_reservations(db, u.id, today=T)

    assert [a["batch_id"] for a in _line(res, e)["allocations"]] == [soon.id, later.id]
    assert _batch(res, soon)["free"] == Decimal("0")
    assert _batch(res, later)["reserved"] == Decimal("30")


async def test_earlier_meal_gets_earlier_batch(db):
    """两餐抢同一批: 日期早的先拿; 同一天午餐先于晚餐。"""
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    soon = await make_stock(db, u, egg, 50, expires_at=SOON)
    later = await make_stock(db, u, egg, 100, expires_at=LATER)
    plan = await make_plan(db, u, start=T, end=T + timedelta(days=7))
    tomorrow = await _meal(db, u, egg, 50, day=T + timedelta(days=1), plan=plan)
    dinner = await _meal(db, u, egg, 50, day=T, meal_type="dinner", plan=plan)
    lunch = await _meal(db, u, egg, 50, day=T, meal_type="lunch", plan=plan)

    res = await compute_reservations(db, u.id, today=T)

    assert _line(res, lunch)["allocations"][0]["batch_id"] == soon.id
    assert _line(res, dinner)["allocations"][0]["batch_id"] == later.id
    assert _line(res, tomorrow)["allocations"][0]["batch_id"] == later.id
    # 批次上的分配按餐次先后排
    assert [a["entry_id"] for a in _batch(res, later)["allocations"]] == [dinner.id, tomorrow.id]


async def test_shortfall_when_not_enough(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    await make_stock(db, u, egg, 30, expires_at=SOON)
    e = await _meal(db, u, egg, 100)

    res = await compute_reservations(db, u.id, today=T)

    assert _line(res, e)["shortfall"] == Decimal("70")
    assert res["shortfalls"] == [{"ingredient_id": egg.id, "amount": Decimal("70")}]


async def test_auto_never_uses_expired_batch(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    old = await make_stock(db, u, egg, 100, expires_at=PAST)
    e = await _meal(db, u, egg, 40)

    res = await compute_reservations(db, u.id, today=T)

    rb = _batch(res, old)
    assert rb["expired"] is True and rb["reserved"] == Decimal("0")
    assert _line(res, e)["shortfall"] == Decimal("40")


async def test_batch_expiring_today_still_usable(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    b = await make_stock(db, u, egg, 100, expires_at=T)
    await _meal(db, u, egg, 40)

    res = await compute_reservations(db, u.id, today=T)

    assert _batch(res, b)["reserved"] == Decimal("40")


async def test_completed_and_past_meals_not_counted(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    b = await make_stock(db, u, egg, 100, expires_at=LATER)
    await _meal(db, u, egg, 30, completed=True)
    await _meal(db, u, egg, 30, day=T - timedelta(days=2))
    future = await _meal(db, u, egg, 20, day=T + timedelta(days=30))   # 全部未来都算

    res = await compute_reservations(db, u.id, today=T)

    assert [e["entry_id"] for e in res["entries"]] == [future.id]
    assert _batch(res, b)["reserved"] == Decimal("20")


async def test_other_users_data_isolated(db):
    u = await make_user(db, clerk="u_a")
    other = await make_user(db, clerk="u_b")
    egg = await make_ingredient(db, "egg")
    mine = await make_stock(db, u, egg, 100, expires_at=LATER)
    await make_stock(db, other, egg, 100, expires_at=SOON)
    await _meal(db, other, egg, 50)

    res = await compute_reservations(db, u.id, today=T)

    assert [b["batch_id"] for b in res["batches"]] == [mine.id]
    assert res["entries"] == []


async def test_returns_ingredient_names_and_units(db):
    u = await make_user(db)
    tofu = await make_ingredient(db, "tofu")
    tofu.nutrition_basis_unit = "块"
    await make_stock(db, u, tofu, 3, expires_at=LATER)
    await db.flush()

    res = await compute_reservations(db, u.id, today=T)

    assert res["ingredients"][tofu.id] == {"name": "tofu", "unit": "块"}


# ---------- 手选(硬预留) ----------

async def test_manual_pick_used_first_even_if_expired(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    old = await make_stock(db, u, egg, 30, expires_at=PAST)
    fresh = await make_stock(db, u, egg, 100, expires_at=LATER)
    e = await _meal(db, u, egg, 50)
    await _pick(db, e, egg, old)

    res = await compute_reservations(db, u.id, today=T)

    ln = _line(res, e)
    assert ln["picked_batch_ids"] == [old.id]
    assert ln["allocations"] == [
        {"batch_id": old.id, "amount": Decimal("30"), "manual": True},
        {"batch_id": fresh.id, "amount": Decimal("20"), "manual": False},   # 不够的自动补
    ]


async def test_picks_taken_in_selected_order(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    soon = await make_stock(db, u, egg, 50, expires_at=SOON)
    later = await make_stock(db, u, egg, 50, expires_at=LATER)
    e = await _meal(db, u, egg, 60)
    await _pick(db, e, egg, later, soon)      # 故意先选后过期的

    res = await compute_reservations(db, u.id, today=T)

    assert [(a["batch_id"], a["amount"]) for a in _line(res, e)["allocations"]] == [
        (later.id, Decimal("50")), (soon.id, Decimal("10")),
    ]


async def test_later_meals_pick_is_hard_earlier_auto_moves(db):
    """后面的餐手选了某批 → 前面餐的自动分配让开, 改用别的批次。"""
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    soon = await make_stock(db, u, egg, 50, expires_at=SOON)
    later = await make_stock(db, u, egg, 100, expires_at=LATER)
    plan = await make_plan(db, u, start=T, end=T + timedelta(days=7))
    first = await _meal(db, u, egg, 50, day=T, plan=plan)
    second = await _meal(db, u, egg, 50, day=T + timedelta(days=1), plan=plan)
    await _pick(db, second, egg, soon)

    res = await compute_reservations(db, u.id, today=T)

    assert _line(res, second)["allocations"][0] == {
        "batch_id": soon.id, "amount": Decimal("50"), "manual": True,
    }
    assert _line(res, first)["allocations"][0]["batch_id"] == later.id


# ---------- 真实扣减与预留一致 ----------

async def test_deduct_uses_pick_then_fresh_fefo(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    soon = await make_stock(db, u, egg, 50, expires_at=SOON)
    later = await make_stock(db, u, egg, 50, expires_at=LATER)
    e = await _meal(db, u, egg, 60)
    await _pick(db, e, egg, later)

    shortfalls = await deduct_for_entry(db, u.id, e, today=T)

    assert shortfalls == []
    assert later.quantity_grams == Decimal("0")      # 手选的先扣光
    assert soon.quantity_grams == Decimal("40")      # 剩 10 走 FEFO


async def test_deduct_skips_expired_unless_picked(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    old = await make_stock(db, u, egg, 100, expires_at=PAST)
    e = await _meal(db, u, egg, 40)

    shortfalls = await deduct_for_entry(db, u.id, e, today=T)

    assert old.quantity_grams == Decimal("100")      # 过期批次不自动扣
    assert shortfalls == [{"ingredient_id": egg.id, "shortfall_grams": Decimal("40")}]


async def test_deduct_respects_other_meals_picks(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    soon = await make_stock(db, u, egg, 50, expires_at=SOON)
    later = await make_stock(db, u, egg, 100, expires_at=LATER)
    plan = await make_plan(db, u, start=T, end=T + timedelta(days=7))
    now = await _meal(db, u, egg, 50, day=T, plan=plan)
    reserved = await _meal(db, u, egg, 30, day=T + timedelta(days=1), plan=plan)
    await _pick(db, reserved, egg, soon)             # 明天那顿手选了早过期批的 30

    await deduct_for_entry(db, u.id, now, today=T)

    assert soon.quantity_grams == Decimal("30")      # 只动了没被手选的 20
    assert later.quantity_grams == Decimal("70")     # 剩 30 从下一批


async def test_deduct_merges_duplicate_ingredient_lines(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    b = await make_stock(db, u, egg, 100, expires_at=LATER)
    v = await make_variant(db, (egg, 20), (egg, 30))
    p = await make_plan(db, u, start=T, end=T)
    e = await make_entry(db, p, v, servings=1, day=T)

    res = await compute_reservations(db, u.id, today=T)
    assert _line(res, e)["need"] == Decimal("50")

    await deduct_for_entry(db, u.id, e, today=T)
    assert b.quantity_grams == Decimal("50")


# ---------- HTTP ----------

async def _api_setup(session, user):
    today = date.today()
    egg = await make_ingredient(session, "egg_api")
    salt = await make_ingredient(session, "salt_api")
    soon = await make_stock(session, user, egg, 50, expires_at=today + timedelta(days=3))
    later = await make_stock(session, user, egg, 100, expires_at=today + timedelta(days=10))
    plan = await make_plan(session, user, start=today, end=today + timedelta(days=7))
    v = await make_variant(session, (egg, 50))
    first = await make_entry(session, plan, v, servings=1, day=today)
    second = await make_entry(session, plan, v, servings=1, day=today + timedelta(days=1))
    return egg, salt, soon, later, plan, first, second


async def test_api_reservations_shape(api_client):
    client, session, user = api_client
    egg, _, soon, _, _, first, _ = await _api_setup(session, user)

    r = await client.get("/inventory/reservations")

    assert r.status_code == 200
    body = r.json()
    assert {"today", "batches", "entries", "shortfalls", "ingredients"} <= set(body)
    assert str(egg.id) in body["ingredients"]
    b = next(x for x in body["batches"] if x["batch_id"] == soon.id)
    assert b["allocations"][0]["entry_id"] == first.id


async def test_api_set_picks_then_clear(api_client):
    client, session, user = api_client
    egg, _, soon, later, plan, first, second = await _api_setup(session, user)
    url = f"/meal-plans/{plan.id}/entries/{second.id}/picks"

    # second 当前自动用 later; later 还有 50 未预留 → 可选
    r = await client.put(url, json={"ingredient_id": egg.id, "inventory_item_ids": [later.id]})
    assert r.status_code == 204
    body = (await client.get("/inventory/reservations")).json()
    ln = next(e for e in body["entries"] if e["entry_id"] == second.id)["lines"][0]
    assert ln["picked_batch_ids"] == [later.id] and ln["allocations"][0]["manual"] is True

    r = await client.put(url, json={"ingredient_id": egg.id, "inventory_item_ids": []})
    assert r.status_code == 204
    body = (await client.get("/inventory/reservations")).json()
    ln = next(e for e in body["entries"] if e["entry_id"] == second.id)["lines"][0]
    assert ln["picked_batch_ids"] == []


async def test_api_rejects_batch_fully_reserved_by_others(api_client):
    client, session, user = api_client
    egg, _, soon, _, plan, _, second = await _api_setup(session, user)
    # soon(50) 被 first 全部占用, second 不能选
    r = await client.put(
        f"/meal-plans/{plan.id}/entries/{second.id}/picks",
        json={"ingredient_id": egg.id, "inventory_item_ids": [soon.id]},
    )
    assert r.status_code == 400


async def test_api_rejects_wrong_ingredient_or_foreign_batch(api_client):
    client, session, user = api_client
    egg, salt, _, _, plan, first, _ = await _api_setup(session, user)
    other = await make_user(session, clerk="someone_else")
    foreign = await make_stock(
        session, other, egg, 100, expires_at=date.today() + timedelta(days=5)
    )
    url = f"/meal-plans/{plan.id}/entries/{first.id}/picks"

    r = await client.put(url, json={"ingredient_id": salt.id, "inventory_item_ids": []})
    assert r.status_code == 400          # 这顿饭不用盐
    r = await client.put(url, json={"ingredient_id": egg.id, "inventory_item_ids": [foreign.id]})
    assert r.status_code == 400          # 别人的批次


async def test_api_cannot_pick_for_completed_meal(api_client):
    client, session, user = api_client
    egg, _, _, later, plan, first, _ = await _api_setup(session, user)
    first.is_completed = True
    await session.flush()

    r = await client.put(
        f"/meal-plans/{plan.id}/entries/{first.id}/picks",
        json={"ingredient_id": egg.id, "inventory_item_ids": [later.id]},
    )
    assert r.status_code == 400
