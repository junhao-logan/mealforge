# tests/meal_plans/test_default_plan.py
"""默认 plan(Quick Log)保护:
- GET /meal-plans 幂等保证默认 plan 存在(plan_type='default')
- 默认 plan 不可删除(400)
- 普通 plan 仍可正常删除(守卫不误伤)
"""
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_list_ensures_default_plan(api_client):
    """列表端点幂等 get-or-create 默认 plan: 列表里必有一个 plan_type='default'。"""
    client, db, user = api_client
    resp = await client.get("/meal-plans")
    assert resp.status_code == 200, resp.text
    plans = resp.json()
    defaults = [p for p in plans if p["plan_type"] == "default"]
    assert len(defaults) == 1        # 恰好一个默认 plan

    # 再调一次仍只有一个(幂等, 不重复建)
    resp2 = await client.get("/meal-plans")
    defaults2 = [p for p in resp2.json() if p["plan_type"] == "default"]
    assert len(defaults2) == 1


async def test_cannot_delete_default_plan(api_client):
    """默认 plan 删除被拒(400), 且删不掉(仍在列表里)。"""
    client, db, user = api_client
    default_id = next(
        p["id"] for p in (await client.get("/meal-plans")).json()
        if p["plan_type"] == "default"
    )

    resp = await client.delete(f"/meal-plans/{default_id}")
    assert resp.status_code == 400, resp.text

    still = [p["id"] for p in (await client.get("/meal-plans")).json()]
    assert default_id in still       # 没被删掉


async def test_regular_plan_still_deletable(api_client):
    """守卫只挡默认 plan: 普通 plan 照常可删(204)。"""
    client, db, user = api_client
    created = await client.post("/meal-plans", json={
        "name": "Cutting week",
        "start_date": "2026-09-01",
        "end_date": "2026-09-07",
        "plan_type": "regular",
    })
    assert created.status_code == 201, created.text
    plan_id = created.json()["id"]

    resp = await client.delete(f"/meal-plans/{plan_id}")
    assert resp.status_code == 204, resp.text
