# tests/meal_plans/test_daily_summary_cache.py
"""daily-summary 的缓存: 命中/存储/失效/降级 + 路由不遮蔽。

用 fakeredis(conftest 的 cache_redis fixture), 不依赖真 Redis 容器。
"""
import pytest

from app.core.cache import summary_key
from tests.factories import make_ingredient, make_variant

pytestmark = pytest.mark.asyncio(loop_scope="session")

DAY = "2026-08-08"


async def _seed_entry(client, db, user, *, variant, meal="lunch", servings=1, day=DAY):
    """经 quick-log 端点造一条餐次(会连带失效缓存, 符合真实路径)。"""
    resp = await client.post("/meal-plans/quick-log", json={
        "recipe_variant_id": variant.id, "meal_type": meal,
        "servings": servings, "scheduled_date": day,
    })
    assert resp.status_code == 201, resp.text
    return resp


async def test_daily_summary_route_not_shadowed(api_client):
    """回归: GET /daily-summary 返回 200, 不被 /{plan_id} 遮蔽成 422。"""
    client, db, user = api_client
    resp = await client.get("/meal-plans/daily-summary", params={"date": DAY})
    assert resp.status_code == 200        # 不是 422


async def test_summary_stores_cache_on_miss(api_client, cache_redis):
    """未命中: 调用后缓存里出现该 key(算完存了)。"""
    client, db, user = api_client
    v = await make_variant(db, (await make_ingredient(db, "tomato"), 100))
    await _seed_entry(client, db, user, variant=v)

    key = summary_key(user.id, DAY)
    assert await cache_redis.get(key) is None      # 造数据时失效过, 现在无缓存
    await client.get("/meal-plans/daily-summary", params={"date": DAY})
    assert await cache_redis.get(key) is not None  # 调用后有了缓存


async def test_summary_served_from_cache(api_client, cache_redis):
    """命中: 缓存里塞一个假值, 端点直接返回它(不重新算)。"""
    client, db, user = api_client
    key = summary_key(user.id, DAY)
    # 手动塞一个"实际不可能算出"的值, 命中则会原样返回
    fake = {
        "date": DAY, "entry_count": 999, "has_goal": False,
        "calories": {"consumed": "0", "target": None, "percent": None},
        "protein_g": {"consumed": "0", "target": None, "percent": None},
        "carbs_g": {"consumed": "0", "target": None, "percent": None},
        "fat_g": {"consumed": "0", "target": None, "percent": None},
    }
    import json
    await cache_redis.set(key, json.dumps(fake))

    resp = await client.get("/meal-plans/daily-summary", params={"date": DAY})
    assert resp.status_code == 200
    assert resp.json()["entry_count"] == 999       # 来自缓存, 不是真算的


async def test_write_invalidates_cache(api_client, cache_redis):
    """失效: 先缓存, 再加餐 → 该天 key 被删。"""
    client, db, user = api_client
    v = await make_variant(db, (await make_ingredient(db, "tomato"), 100))
    await _seed_entry(client, db, user, variant=v)

    # 先调一次, 生成缓存
    await client.get("/meal-plans/daily-summary", params={"date": DAY})
    key = summary_key(user.id, DAY)
    assert await cache_redis.get(key) is not None

    # 再加一餐到同一天 → 失效
    await _seed_entry(client, db, user, variant=v, meal="dinner")
    assert await cache_redis.get(key) is None       # 缓存被删


async def test_recompute_reflects_new_data_after_invalidation(api_client, cache_redis):
    """失效后重算: 加餐后再查, entry_count 反映新数据(不是旧缓存)。"""
    client, db, user = api_client
    v = await make_variant(db, (await make_ingredient(db, "tomato"), 100))
    await _seed_entry(client, db, user, variant=v)                 # 1 餐

    r1 = await client.get("/meal-plans/daily-summary", params={"date": DAY})
    assert r1.json()["entry_count"] == 1

    await _seed_entry(client, db, user, variant=v, meal="dinner")  # +1 = 2 餐
    r2 = await client.get("/meal-plans/daily-summary", params={"date": DAY})
    assert r2.json()["entry_count"] == 2            # 反映最新, 非旧缓存的 1

async def test_summary_degrades_when_redis_fails(api_client):
    """降级: Redis 读写抛错时, daily-summary 仍返回 200(退回查库)。

    注入一个所有操作都抛 RedisError 的 redis, 覆盖 get_redis 依赖。
    cache.py 内部 try/except 兜底 → 端点不受影响。
    """
    from redis.exceptions import RedisError

    from app.core.redis import get_redis
    from app.main import app

    class BrokenRedis:
        async def get(self, *a, **k):
            raise RedisError("down")

        async def set(self, *a, **k):
            raise RedisError("down")

        async def delete(self, *a, **k):
            raise RedisError("down")

    async def _broken():
        yield BrokenRedis()

    client, db, user = api_client
    v = await make_variant(db, (await make_ingredient(db, "tomato"), 100))
    resp0 = await client.post("/meal-plans/quick-log", json={
        "recipe_variant_id": v.id, "meal_type": "lunch",
        "servings": 1, "scheduled_date": DAY,
    })
    assert resp0.status_code == 201        # 写操作即便失效缓存失败也不崩

    app.dependency_overrides[get_redis] = _broken
    try:
        resp = await client.get("/meal-plans/daily-summary", params={"date": DAY})
        assert resp.status_code == 200      # Redis 挂了仍正常返回(降级查库)
        assert resp.json()["entry_count"] == 1
    finally:
        app.dependency_overrides.pop(get_redis, None)