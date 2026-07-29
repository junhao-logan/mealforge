# tests/recipes/test_recipe_visibility.py
import pytest
from sqlalchemy import select

from app.recipes.models import Recipe
from app.users.models import User
from tests.factories import make_ingredient, make_recipe

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _names(resp):
    return [r["name"] for r in resp.json()]


async def test_list_shows_global_and_own_hides_others(api_client):
    """list: 见 global + 自己私有; 不见别人私有。"""
    client, db, user = api_client
    other = User(clerk_user_id="other_recipe_user")
    db.add(other)
    await db.flush()
    await make_recipe(db, "public_dish", visibility="global")
    await make_recipe(db, "my_dish", visibility="private", created_by=user.id)
    await make_recipe(db, "their_dish", visibility="private", created_by=other.id)

    names = await _names(await client.get("/recipes"))
    assert "public_dish" in names
    assert "my_dish" in names
    assert "their_dish" not in names


async def test_get_global_ok(api_client):
    client, db, user = api_client
    r = await make_recipe(db, "g", visibility="global")
    resp = await client.get(f"/recipes/{r.id}")
    assert resp.status_code == 200


async def test_get_own_private_ok(api_client):
    client, db, user = api_client
    r = await make_recipe(db, "mine", visibility="private", created_by=user.id)
    resp = await client.get(f"/recipes/{r.id}")
    assert resp.status_code == 200


async def test_get_others_private_404(api_client):
    """别人的私有菜谱按 id 直取 → 404(不泄漏存在性)。"""
    client, db, user = api_client
    other = User(clerk_user_id="other_recipe_user2")
    db.add(other)
    await db.flush()
    r = await make_recipe(db, "secret", visibility="private", created_by=other.id)
    resp = await client.get(f"/recipes/{r.id}")
    assert resp.status_code == 404


async def test_create_sets_private_owner_source(api_client):
    """POST 创建: visibility=private / source=user / 归属=当前用户。"""
    client, db, user = api_client
    tomato = await make_ingredient(db, "tomato", visibility="global")

    resp = await client.post("/recipes", json={
        "name": "My Stew",
        "variant": {
            "name": "std", "instructions": "cook",
            "ingredients": [
                {"ingredient_id": tomato.id, "input_amount": 100, "input_unit": "g"}
            ],
        },
    })
    assert resp.status_code == 201
    assert resp.json()["visibility"] == "private"

    r = (await db.execute(
        select(Recipe).where(Recipe.name == "My Stew")
    )).scalar_one()
    assert r.created_by_user_id == user.id
    assert r.source == "user"