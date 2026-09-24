# tests/test_hardening.py
"""第 1 批代码审查修复的回归测试: 可见性、输入校验、并发 / 精度、缓存失效等。"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.core.cache import summary_key
from app.core.dates import today_in
from app.inventory.services import deduct_for_entry, restock_for_entry
from app.recipes.services import resolve_quantity
from tests.factories import (
    make_entry,
    make_ingredient,
    make_plan,
    make_shopping_list,
    make_stock,
    make_user,
    make_variant,
)

ASYNC = pytest.mark.asyncio(loop_scope="session")
TODAY = date.today()
FUTURE = TODAY + timedelta(days=10)


async def _secret_ingredient(session):
    """别人的私有食材。"""
    other = await make_user(session, clerk="someone_else")
    return await make_ingredient(session, "secret sauce", visibility="private", created_by=other.id)


# ---------- 可见性(I11): 不能引用别人的私有食材 / 菜谱 ----------

@ASYNC
async def test_recipe_cannot_use_others_private_ingredient(api_client):
    client, session, _ = api_client
    secret = await _secret_ingredient(session)
    r = await client.post("/recipes", json={
        "name": "x", "variant": {"name": "std", "instructions": "x", "ingredients": [
            {"ingredient_id": secret.id, "input_amount": 10, "input_unit": "g"}]},
    })
    assert r.status_code == 404


@ASYNC
async def test_inventory_cannot_use_others_private_ingredient(api_client):
    client, session, _ = api_client
    secret = await _secret_ingredient(session)
    r = await client.post("/inventory", json={"ingredient_id": secret.id, "input_amount": 10})
    assert r.status_code == 404


@ASYNC
async def test_shopping_cannot_use_others_private_or_missing_ingredient(api_client):
    client, session, user = api_client
    secret = await _secret_ingredient(session)
    sl = await make_shopping_list(session, user)
    r = await client.post(f"/shopping-lists/{sl.id}/items",
                          json={"ingredient_id": secret.id, "needed_grams": 5})
    assert r.status_code == 404
    r = await client.post(f"/shopping-lists/{sl.id}/items",
                          json={"ingredient_id": 987654321, "needed_grams": 5})
    assert r.status_code == 404                     # 以前在外键处 500


@ASYNC
async def test_cannot_schedule_others_private_recipe(api_client):
    client, session, user = api_client
    egg = await make_ingredient(session, "egg_vis")
    private_variant = await make_variant(session, (egg, 50), visibility="private")  # 无主私有
    plan = await make_plan(session, user, start=TODAY, end=TODAY)

    r = await client.post("/meal-plans/quick-log", json={
        "recipe_variant_id": private_variant.id, "meal_type": "lunch"})
    assert r.status_code == 404
    r = await client.post(f"/meal-plans/{plan.id}/entries", json={
        "recipe_variant_id": private_variant.id, "meal_type": "lunch",
        "scheduled_date": TODAY.isoformat()})
    assert r.status_code == 404


# ---------- 输入校验: 以前会 500 的输入现在 422 ----------

@ASYNC
async def test_commit_rejects_entry_without_source(api_client):
    client, _, _ = api_client
    r = await client.post("/meal-plans/generate/commit", json={
        "start_date": TODAY.isoformat(),
        "entries": [{"day_offset": 0, "meal_type": "lunch"}],
    })
    assert r.status_code == 422


@ASYNC
async def test_commit_rejects_ingredient_line_without_source(api_client):
    client, _, _ = api_client
    r = await client.post("/meal-plans/generate/commit", json={
        "start_date": TODAY.isoformat(),
        "entries": [{"day_offset": 0, "meal_type": "lunch", "new_recipe": {
            "name": "x", "instructions": "x", "ingredients": [{"amount": 10}]}}],
    })
    assert r.status_code == 422


@ASYNC
@pytest.mark.parametrize("bad", [{"meal_type": "brunch"}, {"day_offset": 99}])
async def test_commit_rejects_bad_meal_type_or_offset(api_client, bad):
    client, _, _ = api_client
    entry = {"day_offset": 0, "meal_type": "lunch", "recipe_variant_id": 1, **bad}
    r = await client.post("/meal-plans/generate/commit",
                          json={"start_date": TODAY.isoformat(), "entries": [entry]})
    assert r.status_code == 422


@ASYNC
async def test_entries_range_validated(api_client):
    client, _, _ = api_client
    r = await client.get("/meal-plans/entries",
                         params={"start": "2026-09-10", "end": "2026-09-01"})
    assert r.status_code == 422


@ASYNC
async def test_nutrition_rejects_unknown_activity(api_client):
    client, _, _ = api_client
    r = await client.put("/users/me/body-metrics", json={"activity_level": "couch_potato"})
    assert r.status_code == 422


def test_resolve_quantity_rejects_overflow():
    class _Ing:
        name = "chicken"
        nutrition_basis_unit = "g"
        default_unit = "piece"
        grams_per_unit = Decimal("120")
        allowed_units = ["piece", "g"]
    with pytest.raises(HTTPException) as e:
        resolve_quantity(_Ing(), Decimal("10000"), "piece")     # 1,200,000 g 超列上限
    assert e.value.status_code == 422


@pytest.mark.parametrize("tz", ["America", "Etc", "Europe"])
def test_timezone_directory_names_fall_back(tz):
    today_in(tz)                                               # 以前 IsADirectoryError → 500


# ---------- 库存 PATCH: 传 null 能清空, 不传不变 ----------

@ASYNC
async def test_patch_can_clear_expiry_and_location(api_client):
    client, session, user = api_client
    egg = await make_ingredient(session, "egg_patch")
    item = await make_stock(session, user, egg, 100, expires_at=FUTURE)
    item.location = "fridge"
    await session.flush()

    r = await client.patch(f"/inventory/{item.id}", json={"quantity_grams": 80})
    assert r.json()["expires_at"] == FUTURE.isoformat()     # 没传 → 不变
    assert r.json()["location"] == "fridge"

    r = await client.patch(f"/inventory/{item.id}", json={"expires_at": None, "location": None})
    assert r.json()["expires_at"] is None and r.json()["location"] is None
    assert Decimal(r.json()["quantity_grams"]) == Decimal("80")


# ---------- 采购 ----------

@ASYNC
async def test_text_only_item_purchase_needs_no_amount(api_client):
    client, session, user = api_client
    sl = await make_shopping_list(session, user)
    item = (await client.post(f"/shopping-lists/{sl.id}/items",
                              json={"item_name": "kitchen paper"})).json()
    r = await client.patch(f"/shopping-lists/{sl.id}/items/{item['id']}/purchase", json={})
    assert r.status_code == 200 and r.json()["is_purchased"] is True


@ASYNC
async def test_purchased_grams_is_canonical_amount(api_client):
    client, session, user = api_client
    chicken = await make_ingredient(session, "chicken_buy")
    chicken.default_unit = "piece"
    chicken.grams_per_unit = Decimal("120")
    sl = await make_shopping_list(session, user)
    await session.flush()
    item = (await client.post(f"/shopping-lists/{sl.id}/items",
                              json={"ingredient_id": chicken.id, "needed_grams": 240})).json()

    r = await client.patch(f"/shopping-lists/{sl.id}/items/{item['id']}/purchase",
                           json={"purchased_amount": 2, "purchased_unit": "piece"})

    assert Decimal(r.json()["purchased_amount"]) == Decimal("2")
    assert Decimal(r.json()["purchased_grams"]) == Decimal("240")   # 以前记成 2


@ASYNC
async def test_create_list_from_plan_with_inverted_window(api_client):
    client, session, user = api_client
    plan = await make_plan(session, user, start=TODAY, end=TODAY + timedelta(days=2))
    r = await client.post("/shopping-lists", json={
        "source_meal_plan_id": plan.id,
        "start_date": (TODAY + timedelta(days=30)).isoformat()})
    assert r.status_code == 422                     # 以前撞 DB CHECK → 500


# ---------- 精度: 完成 / 撤销循环不再凭空多出 0.01 ----------

@ASYNC
async def test_complete_uncomplete_cycle_has_no_rounding_drift(db):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg_round")
    batch = await make_stock(db, u, egg, 100, expires_at=FUTURE)
    v = await make_variant(db, (egg, "33.33"))
    p = await make_plan(db, u, start=TODAY, end=TODAY)
    e = await make_entry(db, p, v, servings="1.5", day=TODAY)   # 需求 49.995

    for _ in range(3):
        await deduct_for_entry(db, u.id, e, today=TODAY)
        await restock_for_entry(db, u.id, e)
    assert batch.quantity_grams == Decimal("100")


# ---------- 营养目标变了 → 所有天的汇总缓存失效 ----------

@ASYNC
async def test_goal_change_invalidates_all_summaries(api_client, cache_redis):
    client, _, user = api_client
    keys = [summary_key(user.id, TODAY), summary_key(user.id, TODAY - timedelta(days=3))]
    for k in keys:
        await cache_redis.set(k, "{}")

    r = await client.put("/users/me/nutrition-goal", json={
        "goal_type": "maintenance", "daily_calories": 2000,
        "daily_protein_g": 150, "daily_carbs_g": 200, "daily_fat_g": 60})

    assert r.status_code == 200
    for k in keys:
        assert await cache_redis.get(k) is None


# ---------- 响应附带名字 / 默认做法(前端不再 N+1 或受 100 条上限影响) ----------

@ASYNC
async def test_recipe_list_has_default_variant_and_detail_has_names(api_client):
    client, session, _ = api_client
    egg = await make_ingredient(session, "egg_names")
    created = (await client.post("/recipes", json={
        "name": "omelette", "variant": {"name": "std", "instructions": "x", "ingredients": [
            {"ingredient_id": egg.id, "input_amount": 100, "input_unit": "g"}]},
    })).json()
    variant_id = created["variants"][0]["id"]

    listed = (await client.get("/recipes", params={"limit": 100})).json()
    row = next(r for r in listed if r["id"] == created["id"])
    assert row["default_variant_id"] == variant_id

    detail = (await client.get(f"/recipes/{created['id']}")).json()
    assert detail["variants"][0]["ingredients"][0]["ingredient_name"] == "egg_names"


@ASYNC
async def test_inventory_list_has_names_and_units(api_client):
    client, session, user = api_client
    tofu = await make_ingredient(session, "tofu_list")
    tofu.nutrition_basis_unit = "块"
    await make_stock(session, user, tofu, 3, expires_at=FUTURE)
    await session.flush()

    rows = (await client.get("/inventory")).json()
    row = next(r for r in rows if r["ingredient_id"] == tofu.id)
    assert row["ingredient_name"] == "tofu_list" and row["unit"] == "块"


# ---------- AI 草稿 → 确认: 能预览的就能确认 ----------

@ASYNC
async def test_commit_accepts_line_with_both_id_and_name(api_client):
    """AI 常把已有食材的名字也带上: 以 ingredient_id 为准, 不应 422。"""
    client, session, _ = api_client
    egg = await make_ingredient(session, "egg_both")
    r = await client.post("/meal-plans/generate/commit", json={
        "start_date": TODAY.isoformat(),
        "entries": [{"day_offset": 0, "meal_type": "lunch", "new_recipe": {
            "name": "egg bowl", "instructions": "x", "ingredients": [
                {"ingredient_id": egg.id, "new_name": "egg", "amount": 50},
                {"ingredient_id": egg.id, "new_name": "", "amount": 10},
            ]}}],
    })
    assert r.status_code == 201, r.text
