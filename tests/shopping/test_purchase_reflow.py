# tests/shopping/test_purchase_reflow.py
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.inventory.models import InventoryItem, InventoryTransaction
from app.shopping.schemas import ShoppingItemCreate
from app.shopping.services import add_manual_item, mark_item_purchased
from tests.factories import (
    make_ingredient, make_shopping_item, make_shopping_list, make_user,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _count(db, model):
    return (await db.execute(select(func.count()).select_from(model))).scalar()


async def test_purchase_inventory_item_reflows(db):
    """打勾入库项: 标记已购 + 建库存批次 + 写 purchase 流水(I9 原子)。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    sl = await make_shopping_list(db, u)
    item = await make_shopping_item(db, sl, ingredient=tomato, needed_grams=400)

    await mark_item_purchased(db, item, u.id, purchased_amount=Decimal("500"))

    assert item.is_purchased is True
    assert item.purchased_grams == Decimal("500")

    batches = (await db.execute(select(InventoryItem))).scalars().all()
    txns = (await db.execute(select(InventoryTransaction))).scalars().all()
    assert len(batches) == 1
    assert batches[0].ingredient_id == tomato.id
    assert batches[0].quantity_grams == Decimal("500")
    assert len(txns) == 1
    assert txns[0].reason == "purchase"
    assert txns[0].delta_grams == Decimal("500")


async def test_purchase_non_inventory_item_no_batch(db):
    """打勾非入库项(厨房纸): 只标记已购, 不建批次/流水。"""
    u = await make_user(db)
    sl = await make_shopping_list(db, u)
    item = await make_shopping_item(
        db, sl, item_name="厨房纸", source="manual", add_to_inventory=False
    )

    await mark_item_purchased(db, item, u.id, purchased_amount=None)

    assert item.is_purchased is True
    assert await _count(db, InventoryItem) == 0
    assert await _count(db, InventoryTransaction) == 0


async def test_purchase_reflow_amount_independent_of_needed(db):
    """回流用实际购买量, 与需求量无关(需求 400, 买 250 → 批次 250)。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    sl = await make_shopping_list(db, u)
    item = await make_shopping_item(db, sl, ingredient=tomato, needed_grams=400)

    await mark_item_purchased(db, item, u.id, purchased_amount=Decimal("250"))

    batch = (await db.execute(select(InventoryItem))).scalar_one()
    assert batch.quantity_grams == Decimal("250")   # 买多少入多少, 不是需求量


async def test_add_manual_ingredient_item(db):
    """加手动食材项: 落库、source=manual。"""
    u = await make_user(db)
    onion = await make_ingredient(db, "onion")
    sl = await make_shopping_list(db, u)

    item = await add_manual_item(db, sl, ShoppingItemCreate(
        ingredient_id=onion.id, needed_grams=Decimal("100"),
    ))

    assert item.id is not None
    assert item.source == "manual"
    assert item.ingredient_id == onion.id
    assert item.add_to_inventory is True


async def test_add_manual_text_item(db):
    """加手动纯文本项(厨房纸): item_name + 不入库。"""
    u = await make_user(db)
    sl = await make_shopping_list(db, u)

    item = await add_manual_item(db, sl, ShoppingItemCreate(
        item_name="厨房纸", add_to_inventory=False,
    ))

    assert item.source == "manual"
    assert item.item_name == "厨房纸"
    assert item.ingredient_id is None
    assert item.add_to_inventory is False