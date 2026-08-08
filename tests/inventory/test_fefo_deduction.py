# tests/inventory/test_fefo_deduction.py
"""FEFO 先进先出扣减的行为契约(招牌 deep-dive 故事的回归保护)。"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.inventory.models import InventoryTransaction
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

D1 = date(2026, 1, 10)   # 早过期
D2 = date(2026, 1, 20)   # 晚过期


async def _entry_needing(db, user, ingredient, grams, servings=1):
    """建一个餐次: 需要 ingredient grams 克(× servings)。"""
    v = await make_variant(db, (ingredient, grams))
    p = await make_plan(db, user)
    return await make_entry(db, p, v, servings=servings)


async def test_deducts_earliest_expiry_first(db):
    """两批: 早过期的先扣(FEFO 核心)。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    late = await make_stock(db, u, tomato, 100, expires_at=D2)   # 晚过期
    early = await make_stock(db, u, tomato, 100, expires_at=D1)  # 早过期
    entry = await _entry_needing(db, u, tomato, 60)

    shortfalls = await deduct_for_entry(db, u.id, entry)

    assert shortfalls == []
    assert early.quantity_grams == Decimal("40")   # 早过期的被扣 60
    assert late.quantity_grams == Decimal("100")   # 晚过期的没动


async def test_crosses_batches_when_one_not_enough(db):
    """一批不够 → 跨到下一批继续扣。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    early = await make_stock(db, u, tomato, 50, expires_at=D1)
    late = await make_stock(db, u, tomato, 100, expires_at=D2)
    entry = await _entry_needing(db, u, tomato, 80)   # 需 80: 早批 50 全扣 + 晚批 30

    await deduct_for_entry(db, u.id, entry)

    assert early.quantity_grams == Decimal("0")     # 早批扣光
    assert late.quantity_grams == Decimal("70")     # 晚批扣 30


async def test_null_expiry_sorted_last(db):
    """无过期日的批次排最后(NULLS LAST): 有过期日的先扣。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    no_exp = await make_stock(db, u, tomato, 100, expires_at=None)
    has_exp = await make_stock(db, u, tomato, 100, expires_at=D2)
    entry = await _entry_needing(db, u, tomato, 60)

    await deduct_for_entry(db, u.id, entry)

    assert has_exp.quantity_grams == Decimal("40")  # 有过期日的先扣
    assert no_exp.quantity_grams == Decimal("100")  # 无过期日的留最后


async def test_shortfall_when_insufficient_no_underflow(db):
    """库存不足: 扣到 0 不下穿, 差额作为短缺返回。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    b = await make_stock(db, u, tomato, 30, expires_at=D1)
    entry = await _entry_needing(db, u, tomato, 100)   # 需 100, 只有 30

    shortfalls = await deduct_for_entry(db, u.id, entry)

    assert b.quantity_grams == Decimal("0")            # 扣光, 不为负
    assert len(shortfalls) == 1
    assert shortfalls[0]["ingredient_id"] == tomato.id
    assert shortfalls[0]["shortfall_grams"] == Decimal("70")   # 差 70


async def test_records_transaction_per_deduction(db):
    """每笔扣减记一条 meal_consumption 流水(负数, 关联餐次)。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    await make_stock(db, u, tomato, 100, expires_at=D1)
    entry = await _entry_needing(db, u, tomato, 60)

    await deduct_for_entry(db, u.id, entry)

    txns = (await db.execute(
        select(InventoryTransaction).where(
            InventoryTransaction.reason == "meal_consumption")
    )).scalars().all()
    assert len(txns) == 1
    assert txns[0].delta_grams == Decimal("-60")       # 扣减为负
    assert txns[0].source_entry_id == entry.id


async def test_servings_multiplies_demand(db):
    """需求 = 配料克数 × 份数(I13 配方倍数)。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    b = await make_stock(db, u, tomato, 500, expires_at=D1)
    entry = await _entry_needing(db, u, tomato, 100, servings=3)   # 100 × 3 = 300

    await deduct_for_entry(db, u.id, entry)

    assert b.quantity_grams == Decimal("200")          # 500 - 300


async def test_same_expiry_ordered_by_purchase_then_id(db):
    """同过期日: 按 purchased_at 先买先扣(FEFO 的确定性兜底)。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    later_buy = await make_stock(db, u, tomato, 100, expires_at=D1,
                                 purchased_at=date(2026, 1, 5))
    earlier_buy = await make_stock(db, u, tomato, 100, expires_at=D1,
                                   purchased_at=date(2026, 1, 1))
    entry = await _entry_needing(db, u, tomato, 60)

    await deduct_for_entry(db, u.id, entry)

    assert earlier_buy.quantity_grams == Decimal("40")  # 先买的先扣
    assert later_buy.quantity_grams == Decimal("100")