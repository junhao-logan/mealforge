# tests/ai/test_generate_endpoint.py
import pytest

import app.ai.services as svc
from app.ai.client import AiError, AiResult
from tests.factories import make_ingredient, make_stock

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed(db, user):
    tomato = await make_ingredient(db, "tomato", visibility="global")
    await make_stock(db, user, tomato, 500)
    return tomato


async def test_generate_endpoint_success(api_client, monkeypatch):
    """POST /recipes/generate: mock AI → 201 + 菜谱。"""
    client, db, user = api_client
    tomato = await _seed(db, user)

    async def fake_raw(prompt):
        return AiResult(tool_input={
            "name": "番茄料理", "servings": 2, "instructions": "做",
            "ingredients": [{"ingredient_id": tomato.id, "amount_grams": 200}],
        }, input_tokens=1000, output_tokens=500)
    monkeypatch.setattr(svc, "generate_recipe_raw", fake_raw)

    resp = await client.post("/recipes/generate", json={"cuisine": "chinese"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "番茄料理"


async def test_generate_endpoint_empty_inventory_400(api_client, monkeypatch):
    """空库存 → 400。"""
    client, db, user = api_client  # 没放库存

    async def fake_raw(prompt):
        raise AssertionError("不该调 AI")
    monkeypatch.setattr(svc, "generate_recipe_raw", fake_raw)

    resp = await client.post("/recipes/generate", json={})
    assert resp.status_code == 400


async def test_generate_endpoint_ai_failure_502(api_client, monkeypatch):
    """AI 侧失败 → 502。"""
    client, db, user = api_client
    await _seed(db, user)

    async def fake_raw(prompt):
        raise AiError("超时")
    monkeypatch.setattr(svc, "generate_recipe_raw", fake_raw)

    resp = await client.post("/recipes/generate", json={})
    assert resp.status_code == 502