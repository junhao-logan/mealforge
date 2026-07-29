# tests/ingredients/test_ingredient_visibility.py
import pytest
from sqlalchemy import select

from app.ingredients.models import Ingredient
from app.users.models import User
from tests.factories import make_ingredient

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _names(resp):
    return [i["name"] for i in resp.json()]


async def test_list_shows_global(api_client):
    """global 食材对所有人可见。"""
    client, db, user = api_client
    await make_ingredient(db, "salt", visibility="global")
    resp = await client.get("/ingredients")
    assert resp.status_code == 200
    assert "salt" in await _names(resp)


async def test_list_shows_own_private(api_client):
    """自己建的私有食材, 自己看得见。"""
    client, db, user = api_client
    await make_ingredient(db, "grandma_sauce", visibility="private", created_by=user.id)
    resp = await client.get("/ingredients")
    assert "grandma_sauce" in await _names(resp)


async def test_list_hides_others_private(api_client):
    """别人的私有食材, 我看不见(可见性过滤核心)。"""
    client, db, user = api_client
    other = User(clerk_user_id="other_ing_user")
    db.add(other)
    await db.flush()
    await make_ingredient(db, "secret_item", visibility="private", created_by=other.id)
    resp = await client.get("/ingredients")
    assert "secret_item" not in await _names(resp)


async def test_create_sets_private_owner_and_source(api_client):
    """POST 创建: 服务端固定 visibility=private / source=user / 归属=当前用户。"""
    client, db, user = api_client
    resp = await client.post(
        "/ingredients",
        json={"name": "My Tofu", "per_100g_protein": 8, "category": "protein"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["visibility"] == "private"
    assert body["name"] == "My Tofu"

    ing = (await db.execute(
        select(Ingredient).where(Ingredient.name == "My Tofu")
    )).scalar_one()
    assert ing.created_by_user_id == user.id
    assert ing.source == "user"
    assert ing.name_normalized == "my tofu"   # 服务端 normalize


async def test_created_ingredient_appears_in_own_list(api_client):
    """自建后, 出现在自己的列表里。"""
    client, db, user = api_client
    await client.post("/ingredients", json={"name": "My Kimchi"})
    resp = await client.get("/ingredients")
    assert "My Kimchi" in await _names(resp)


async def test_name_filter_respects_visibility(api_client):
    """name 搜索也受可见性约束: 搜不到别人的私有。"""
    client, db, user = api_client
    other = User(clerk_user_id="other_ing_user2")
    db.add(other)
    await db.flush()
    await make_ingredient(db, "zzz_public", visibility="global")
    await make_ingredient(db, "zzz_private", visibility="private", created_by=other.id)
    resp = await client.get("/ingredients", params={"name": "zzz"})
    names = await _names(resp)
    assert "zzz_public" in names
    assert "zzz_private" not in names