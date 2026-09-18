# tests/ingredients/test_list_sort_scope.py
"""GET /ingredients 的 sort(recent/name) 与 scope(mine/all) 参数。"""
import pytest

from app.users.models import User
from tests.factories import make_ingredient

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _names(resp):
    return [i["name"] for i in resp.json()]


async def test_sort_recent_newest_first(api_client):
    """sort=recent: 后建的排前面(id 倒序)。"""
    client, db, user = api_client
    await make_ingredient(db, "zzz_old", visibility="global")
    await make_ingredient(db, "zzz_new", visibility="global")
    resp = await client.get("/ingredients", params={"name": "zzz", "sort": "recent"})
    names = await _names(resp)
    assert names.index("zzz_new") < names.index("zzz_old")


async def test_sort_name_alphabetical(api_client):
    """sort=name: 按名字 A-Z。"""
    client, db, user = api_client
    await make_ingredient(db, "sortb_banana", visibility="global")
    await make_ingredient(db, "sorta_apple", visibility="global")
    resp = await client.get("/ingredients", params={"name": "sort", "sort": "name"})
    names = await _names(resp)
    assert names.index("sorta_apple") < names.index("sortb_banana")


async def test_scope_mine_only_own(api_client):
    """scope=mine: 只返回自己创建的, 不含公共库。"""
    client, db, user = api_client
    await make_ingredient(db, "mine_scope_tofu", visibility="private", created_by=user.id)
    await make_ingredient(db, "public_scope_salt", visibility="global")
    resp = await client.get("/ingredients", params={"scope": "mine"})
    names = await _names(resp)
    assert "mine_scope_tofu" in names
    assert "public_scope_salt" not in names


async def test_scope_mine_excludes_others_private(api_client):
    """scope=mine 也不含别人的私有。"""
    client, db, user = api_client
    other = User(clerk_user_id="other_scope_user")
    db.add(other)
    await db.flush()
    await make_ingredient(db, "others_secret", visibility="private", created_by=other.id)
    resp = await client.get("/ingredients", params={"scope": "mine"})
    assert "others_secret" not in await _names(resp)
