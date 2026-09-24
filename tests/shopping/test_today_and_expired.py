# tests/shopping/test_today_and_expired.py
"""A4.2「今天」按请求头时区算; A4.1 采购缺口 / 预扣视图不把过期库存算作「有」。"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.dates import today_in
from app.shopping.services import compute_preview, compute_shortfall
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

# 同步 / 异步测试混排: 异步的逐个标记(Week 9 教训), 不用模块级 pytestmark
ASYNC = pytest.mark.asyncio(loop_scope="session")


# ---------- A4.2 today_in ----------

def test_today_in_valid_timezone():
    # UTC+14 与 UTC-11 相差 25 小时, 当地日期必然不同
    assert today_in("Pacific/Kiritimati") != today_in("Pacific/Pago_Pago")


@pytest.mark.parametrize("bad", [None, "", "Not/AZone", "../../etc/passwd", "x" * 200])
def test_today_in_falls_back_to_utc(bad):
    assert today_in(bad) == datetime.now(UTC).date()


@ASYNC
async def test_header_decides_today(api_client):
    client, _, _ = api_client
    east = await client.get("/inventory/reservations", headers={"X-Timezone": "Pacific/Kiritimati"})
    west = await client.get("/inventory/reservations", headers={"X-Timezone": "Pacific/Pago_Pago"})
    none = await client.get("/inventory/reservations")

    assert east.json()["today"] == today_in("Pacific/Kiritimati").isoformat()
    assert west.json()["today"] == today_in("Pacific/Pago_Pago").isoformat()
    assert none.json()["today"] == datetime.now(UTC).date().isoformat()


# ---------- A4.1 过期库存不算「有」 ----------

async def _setup(db, *, expires_at, grams=100, need=60):
    u = await make_user(db)
    egg = await make_ingredient(db, "egg")
    await make_stock(db, u, egg, grams, expires_at=expires_at)
    v = await make_variant(db, (egg, need))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=1, day=TODAY)
    return u, egg


@ASYNC
async def test_shortfall_ignores_expired_stock(db):
    u, egg = await _setup(db, expires_at=TODAY - timedelta(days=1))

    out = await compute_shortfall(db, u.id, TODAY, WEEK_END, today=TODAY)

    assert out == [{"ingredient_id": egg.id, "shortfall_grams": Decimal("60.00")}]


@ASYNC
async def test_stock_expiring_today_still_counts(db):
    u, _ = await _setup(db, expires_at=TODAY)

    assert await compute_shortfall(db, u.id, TODAY, WEEK_END, today=TODAY) == []


@ASYNC
async def test_preview_actual_excludes_expired(db):
    u, egg = await _setup(db, expires_at=TODAY - timedelta(days=1))

    [row] = await compute_preview(db, u.id, TODAY, WEEK_END, today=TODAY)

    assert row["ingredient_id"] == egg.id
    assert row["actual_grams"] == Decimal("0")
    assert row["projected_remaining_grams"] == Decimal("-60.00")
