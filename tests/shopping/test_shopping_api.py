# tests/shopping/test_shopping_api.py
from datetime import date, timedelta

import pytest

from tests.factories import (
    make_entry,
    make_ingredient,
    make_plan,
    make_shopping_item,
    make_shopping_list,
    make_variant,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

TODAY = date(2026, 6, 1)
END = TODAY + timedelta(days=6)


async def test_generate_endpoint_returns_items(api_client):
    """POST /shopping-lists: 从计划生成, 返回 201 + auto 条目。"""
    client, db, user = api_client
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p = await make_plan(db, user, start=TODAY, end=END)
    await make_entry(db, p, v, servings=2, day=TODAY)

    resp = await client.post("/shopping-lists", json={"source_meal_plan_id": p.id})
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_meal_plan_id"] == p.id
    assert len(body["items"]) == 1
    assert body["items"][0]["source"] == "auto"
    assert body["items"][0]["needed_grams"] == "400.00"


async def test_generate_requires_window(api_client):
    """既没给计划也没给日期 → 422(schema 校验)。"""
    client, db, user = api_client
    resp = await client.post("/shopping-lists", json={})
    assert resp.status_code == 422


async def test_purchase_guard_missing_amount(api_client):
    """入库项打勾未填购买量 → 422。"""
    client, db, user = api_client
    tomato = await make_ingredient(db, "tomato")
    sl = await make_shopping_list(db, user, start=TODAY, end=END)
    item = await make_shopping_item(db, sl, ingredient=tomato, needed_grams=400)

    resp = await client.patch(
        f"/shopping-lists/{sl.id}/items/{item.id}/purchase", json={}
    )
    assert resp.status_code == 422


async def test_purchase_guard_double_purchase(api_client):
    """重复打勾 → 400(防重复回流)。"""
    client, db, user = api_client
    tomato = await make_ingredient(db, "tomato")
    sl = await make_shopping_list(db, user, start=TODAY, end=END)
    item = await make_shopping_item(db, sl, ingredient=tomato, needed_grams=400)

    r1 = await client.patch(
        f"/shopping-lists/{sl.id}/items/{item.id}/purchase",
        json={"purchased_amount": 500},
    )
    assert r1.status_code == 200
    r2 = await client.patch(
        f"/shopping-lists/{sl.id}/items/{item.id}/purchase",
        json={"purchased_amount": 300},
    )
    assert r2.status_code == 400


async def test_ownership_returns_404(api_client):
    """访问别人的清单 → 404(不泄漏存在性)。"""
    client, db, user = api_client
    from app.users.models import User
    other = User(clerk_user_id="other_user")
    db.add(other)
    await db.flush()
    other_list = await make_shopping_list(db, other, start=TODAY, end=END)

    resp = await client.get(f"/shopping-lists/{other_list.id}")
    assert resp.status_code == 404


async def test_add_manual_item_endpoint(api_client):
    """POST /{id}/items: 加纯文本手动项 → 201。"""
    client, db, user = api_client
    sl = await make_shopping_list(db, user, start=TODAY, end=END)

    resp = await client.post(
        f"/shopping-lists/{sl.id}/items",
        json={"item_name": "厨房纸", "add_to_inventory": False},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["item_name"] == "厨房纸"
    assert body["source"] == "manual"