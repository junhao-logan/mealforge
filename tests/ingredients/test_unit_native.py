# tests/ingredients/test_unit_native.py
"""A2 单位本位食材: 用户自建食材可选自己的单位(块/个), 营养按"每N单位"记,
库存/菜谱只用该单位、不给克; 质量食材(g/ml)仍可用克 + 份量单位。"""
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.ingredients.models import Ingredient
from app.inventory.models import InventoryItem

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_create_unit_native_ingredient(api_client):
    """自建"块"本位食材: allowed_units 只有块, default_unit/grams_per_unit 被派生。"""
    client, db, user = api_client
    resp = await client.post("/ingredients", json={
        "name": "自制豆腐块",
        "nutrition_basis_amount": 1,
        "nutrition_basis_unit": "块",
        "per_100g_calories": 200,   # 每 1 块 = 200 kcal(字段名沿用, 语义=每基准)
        "per_100g_protein": 12,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["nutrition_basis_unit"] == "块"
    assert body["nutrition_basis_amount"] == "1.00"
    assert body["allowed_units"] == ["块"]          # 只给块, 不给克

    ing = (await db.execute(
        select(Ingredient).where(Ingredient.name == "自制豆腐块")
    )).scalar_one()
    assert ing.default_unit == "块"                 # 派生 = 规范单位
    assert ing.grams_per_unit == Decimal("1.00")    # 不使用


async def test_add_inventory_unit_native(api_client):
    """给"块"食材加库存 3 块 → quantity_grams 存 3(规范单位下的量)。"""
    client, db, user = api_client
    r = await client.post("/ingredients", json={
        "name": "卤蛋", "nutrition_basis_amount": 1, "nutrition_basis_unit": "个",
        "per_100g_calories": 70,
    })
    ing_id = r.json()["id"]
    resp = await client.post("/inventory", json={
        "ingredient_id": ing_id, "input_amount": 3, "input_unit": "个",
    })
    assert resp.status_code == 201
    item = (await db.execute(
        select(InventoryItem).where(InventoryItem.ingredient_id == ing_id)
    )).scalar_one()
    assert item.quantity_grams == Decimal("3.00")
    assert item.input_unit == "个"


async def test_inventory_rejects_grams_for_unit_native(api_client):
    """"个"本位食材不接受克(422)。"""
    client, db, user = api_client
    r = await client.post("/ingredients", json={
        "name": "包子", "nutrition_basis_amount": 1, "nutrition_basis_unit": "个",
    })
    ing_id = r.json()["id"]
    resp = await client.post("/inventory", json={
        "ingredient_id": ing_id, "input_amount": 100, "input_unit": "g",
    })
    assert resp.status_code == 422


async def test_mass_ingredient_allows_portion_and_grams(api_client):
    """质量食材(规范单位 g)带份量单位 piece: allowed_units=[piece,g];
    加库存 2 piece → 换算 240g。"""
    client, db, user = api_client
    ing = Ingredient(
        name="chicken breast", name_normalized="chicken breast",
        visibility="global",
        nutrition_basis_amount=Decimal("100"), nutrition_basis_unit="g",
        default_unit="piece", grams_per_unit=Decimal("120"),
    )
    db.add(ing)
    await db.flush()
    assert ing.allowed_units == ["piece", "g"]

    resp = await client.post("/inventory", json={
        "ingredient_id": ing.id, "input_amount": 2, "input_unit": "piece",
    })
    assert resp.status_code == 201
    item = (await db.execute(
        select(InventoryItem).where(InventoryItem.ingredient_id == ing.id)
    )).scalar_one()
    assert item.quantity_grams == Decimal("240.00")   # 2 × 120


async def test_nutrition_unit_native_via_recipe(api_client):
    """营养按基准比例算(端到端): "每1块=200kcal"食材, 菜谱用 2 块 → variant 400 kcal。"""
    client, db, user = api_client
    r = await client.post("/ingredients", json={
        "name": "豆腐块nutri", "nutrition_basis_amount": 1, "nutrition_basis_unit": "块",
        "per_100g_calories": 200, "per_100g_protein": 12,
    })
    ing_id = r.json()["id"]
    resp = await client.post("/recipes", json={
        "name": "豆腐煲",
        "variant": {
            "name": "豆腐煲", "instructions": "炖",
            "ingredients": [
                {"ingredient_id": ing_id, "input_amount": 2, "input_unit": "块"}
            ],
        },
    })
    assert resp.status_code == 201
    v = resp.json()["variants"][0]
    assert float(v["total_calories"]) == 400.0   # 200 × 2 / 1
    assert float(v["total_protein_g"]) == 24.0    # 12 × 2 / 1
