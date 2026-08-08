# tests/ai/test_meal_plan_endpoint.py
import pytest

import app.ai.services as svc
from app.ai.client import AiError, AiResult
from tests.factories import make_ingredient, make_variant

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_generate_plan_endpoint_success(api_client, monkeypatch):
    """POST /meal-plans/generate: mock AI → 201 + 计划(含 entries)。"""
    client, db, user = api_client
    tomato = await make_ingredient(db, "tomato", visibility="global")
    v = await make_variant(db, (tomato, 100))

    async def fake_raw(prompt):
        return AiResult(tool_input={"entries": [
            {"day_offset": 0, "meal_type": "lunch", "recipe_variant_id": v.id, "servings": 1},
            {"day_offset": 0, "meal_type": "dinner", "recipe_variant_id": v.id, "servings": 1},
        ]}, input_tokens=500, output_tokens=200)
    monkeypatch.setattr(svc, "generate_meal_plan_raw", fake_raw)

    resp = await client.post("/meal-plans/generate", json={"days": 1})
    assert resp.status_code == 201
    body = resp.json()
    assert body["plan_type"] == "ai_generated"
    assert len(body["entries"]) == 2


async def test_generate_plan_endpoint_empty_400(api_client, monkeypatch):
    """无可用菜谱 → 400。"""
    client, db, user = api_client

    async def fake_raw(prompt):
        raise AssertionError("不该调 AI")
    monkeypatch.setattr(svc, "generate_meal_plan_raw", fake_raw)

    resp = await client.post("/meal-plans/generate", json={"days": 3})
    assert resp.status_code == 400


async def test_generate_plan_endpoint_ai_fail_502(api_client, monkeypatch):
    """AI 失败 → 502。"""
    client, db, user = api_client
    tomato = await make_ingredient(db, "tomato", visibility="global")
    await make_variant(db, (tomato, 100))

    async def fake_raw(prompt):
        raise AiError("超时")
    monkeypatch.setattr(svc, "generate_meal_plan_raw", fake_raw)

    resp = await client.post("/meal-plans/generate", json={})
    assert resp.status_code == 502