# tests/shopping/test_compute_shortfall.py
from datetime import timedelta
from decimal import Decimal

import pytest

from app.shopping.services import compute_shortfall
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


def _gap(result, ingredient_id):
    """从结果里取某食材的缺口; 不在结果里返回 None。"""
    for r in result:
        if r["ingredient_id"] == ingredient_id:
            return r["shortfall_grams"]
    return None


async def test_basic_shortfall(db):
    """需求 > 库存 → 返回差额。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=2)          # 需求 400
    await make_stock(db, u, tomato, 250)            # 库存 250
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert _gap(out, tomato.id) == Decimal("150.00")


async def test_enough_stock_excluded(db):
    """库存 ≥ 需求 → 不出现在缺口里。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=1)          # 需求 200
    await make_stock(db, u, tomato, 500)            # 库存充足
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert _gap(out, tomato.id) is None


async def test_completed_entry_not_counted(db):
    """已完成 entry 不计入需求(双重计数护栏)。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=2, completed=True)   # 已完成 → 不算
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert out == []


async def test_past_dated_entry_excluded(db):
    """scheduled_date < 窗口起点 的漏做餐不进采购(D2)。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=2, day=TODAY - timedelta(days=3))  # 过去
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert out == []


async def test_same_variant_multiple_entries_accumulate(db):
    """同一 variant 多餐: 份数累加(2 + 1.5 = 3.5×)。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=2, day=TODAY)
    await make_entry(db, p, v, servings=Decimal("1.5"), day=TODAY + timedelta(days=1))
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert _gap(out, tomato.id) == Decimal("700.00")   # 200*3.5


async def test_multi_ingredient_aggregation(db):
    """一餐多味, 各食材独立聚合。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    egg = await make_ingredient(db, "egg")
    v = await make_variant(db, (tomato, 200), (egg, 120))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=2)
    await make_stock(db, u, tomato, 100)
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert _gap(out, tomato.id) == Decimal("300.00")   # 400-100
    assert _gap(out, egg.id) == Decimal("240.00")      # 240-0


async def test_empty_window_returns_empty(db):
    """窗口内无未完成 entry → []。"""
    u = await make_user(db)
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert out == []


async def test_user_isolation(db):
    """别人的 entry/库存不串进来(JOIN 用户过滤)。"""
    u1 = await make_user(db, "u1")
    u2 = await make_user(db, "u2")
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, 200))
    p2 = await make_plan(db, u2)
    await make_entry(db, p2, v, servings=5)         # u2 的餐
    await make_stock(db, u2, tomato, 0)
    out = await compute_shortfall(db, u1.id, TODAY, WEEK_END)   # 查 u1
    assert out == []


async def test_subcent_gap_not_emitted(db):
    """量化: 需求超库存不足 0.01g 时不生成微缺口。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    v = await make_variant(db, (tomato, Decimal("100.25")))
    p = await make_plan(db, u)
    await make_entry(db, p, v, servings=Decimal("2.5"))   # 100.25*2.5 = 250.625
    await make_stock(db, u, tomato, Decimal("250.62"))    # 差 0.005 → 量化后 0
    out = await compute_shortfall(db, u.id, TODAY, WEEK_END)
    assert _gap(out, tomato.id) is None