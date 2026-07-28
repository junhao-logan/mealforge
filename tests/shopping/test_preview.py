# tests/shopping/test_preview.py
from datetime import date
from decimal import Decimal

import pytest

from app.shopping.services import compute_preview
from tests.factories import (
    TODAY,
    WEEK_END,
    make_entry,
    make_ingredient,
    make_plan,
    make_stock,
    make_user,
    make_variant,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _row(rows, ingredient_id):
    for r in rows:
        if r["ingredient_id"] == ingredient_id:
            return r
    return None


async def test_preview_projected_can_be_negative(db):
    """库存 250、需求 400 → 预计剩余 -150(负 = 会缺)。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=2)          # 需求 400
    await make_stock(db, u, tomato, 250)            # 库存 250

    row = _row(await compute_preview(db, u.id, TODAY, WEEK_END), tomato.id)
    assert row["actual_grams"] == Decimal("250.00")
    assert row["demand_grams"] == Decimal("400.00")
    assert row["projected_remaining_grams"] == Decimal("-150.00")


async def test_preview_positive_when_enough(db):
    """库存够 → 预计剩余为正。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=1)          # 需求 200
    await make_stock(db, u, tomato, 500)

    row = _row(await compute_preview(db, u.id, TODAY, WEEK_END), tomato.id)
    assert row["projected_remaining_grams"] == Decimal("300.00")


async def test_preview_includes_stock_without_demand(db):
    """有库存但计划里没用到 → 也出现, 预计剩余 = 实际。"""
    u = await make_user(db)
    onion = await make_ingredient(db, "onion")
    await make_stock(db, u, onion, 300)             # 有库存, 无餐次用它

    row = _row(await compute_preview(db, u.id, TODAY, WEEK_END), onion.id)
    assert row["actual_grams"] == Decimal("300.00")
    assert row["demand_grams"] == Decimal("0.00")
    assert row["projected_remaining_grams"] == Decimal("300.00")


async def test_preview_includes_demand_without_stock(db):
    """有需求但零库存 → 出现, 预计剩余为负(全缺)。"""
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    v = await make_variant(db, (egg, 120))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=2)          # 需求 240, 无库存

    row = _row(await compute_preview(db, u.id, TODAY, WEEK_END), egg.id)
    assert row["actual_grams"] == Decimal("0")
    assert row["projected_remaining_grams"] == Decimal("-240.00")


async def test_preview_endpoint_and_route_order(api_client):
    """GET /shopping-lists/preview: 端点可达且不被 /{list_id} 吃掉。"""
    client, db, user = api_client
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p = await make_plan(db, user, start=date(2026, 6, 1), end=date(2026, 6, 7))
    await make_entry(db, p, v, servings=2, day=date(2026, 6, 1))

    resp = await client.get(
        "/shopping-lists/preview",
        params={"start_date": "2026-06-01", "end_date": "2026-06-07"},
    )
    assert resp.status_code == 200      # 不是 422(说明没被当成 list_id)
    body = resp.json()
    assert any(r["ingredient_id"] == tomato.id
               and r["projected_remaining_grams"] == "-400.00" for r in body)