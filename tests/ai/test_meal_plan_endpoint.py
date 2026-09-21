# tests/ai/test_meal_plan_endpoint.py
import pytest

import app.ai.services as svc
from app.ai.client import AiError, AiResult
from tests.factories import make_ingredient, make_variant

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_generate_plan_endpoint_returns_draft(api_client, monkeypatch):
    """POST /meal-plans/generate: mock AI → 200 + 草稿(不落库)。"""
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
    assert resp.status_code == 200
    body = resp.json()
    assert body["days"] == 1
    assert len(body["entries"]) == 2
    assert body["entries"][0]["recipe_variant_id"] == v.id
    assert "recipe_name" in body["entries"][0]


async def test_commit_draft_creates_plan(api_client, monkeypatch):
    """确认草稿 → 新建 ai_generated 计划 + 追加 entries。"""
    client, db, user = api_client
    tomato = await make_ingredient(db, "tomato", visibility="global")
    v = await make_variant(db, (tomato, 100))

    resp = await client.post("/meal-plans/generate/commit", json={
        "start_date": "2026-08-10",
        "entries": [
            {"day_offset": 0, "meal_type": "lunch", "recipe_variant_id": v.id, "servings": 1},
            {"day_offset": 1, "meal_type": "dinner", "recipe_variant_id": v.id, "servings": 2},
        ],
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["plan_type"] == "ai_generated"
    assert len(body["entries"]) == 2


async def test_commit_appends_to_existing_plan(api_client, monkeypatch):
    """确认草稿 → 追加进已有计划, 不清空原有 entries。"""
    client, db, user = api_client
    tomato = await make_ingredient(db, "tomato", visibility="global")
    v = await make_variant(db, (tomato, 100))
    # 建一个普通计划 + 先放一条
    created = await client.post("/meal-plans", json={
        "name": "wk", "start_date": "2026-08-10", "end_date": "2026-08-10",
        "plan_type": "regular",
    })
    plan_id = created.json()["id"]
    await client.post(f"/meal-plans/{plan_id}/entries", json={
        "scheduled_date": "2026-08-10", "meal_type": "breakfast",
        "recipe_variant_id": v.id, "servings": 1,
    })

    resp = await client.post("/meal-plans/generate/commit", json={
        "target_plan_id": plan_id,
        "start_date": "2026-08-10",
        "entries": [
            {"day_offset": 0, "meal_type": "lunch", "recipe_variant_id": v.id, "servings": 1},
        ],
    })
    assert resp.status_code == 201, resp.text
    assert len(resp.json()["entries"]) == 2       # 原有 1 + 追加 1


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