# tests/recipes/test_recommendations.py
import pytest

from app.recipes.services import recommend_recipes
from tests.factories import make_ingredient, make_stock, make_user, make_variant

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_full_match_ranked_first(db):
    """库存备齐所有配料 → missing_count=0, 排最前。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    egg = await make_ingredient(db, "egg")
    await make_variant(db, (tomato, 100), (egg, 50))
    await make_stock(db, u, tomato, 200)
    await make_stock(db, u, egg, 100)

    recs = await recommend_recipes(db, u, max_missing=2)
    assert len(recs) == 1
    assert recs[0]["missing_count"] == 0
    assert recs[0]["missing_ingredients"] == []


async def test_missing_within_threshold_listed(db):
    """缺 1 样(≤max_missing) → 推荐并列出缺的。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    garlic = await make_ingredient(db, "garlic")
    await make_variant(db, (tomato, 100), (garlic, 10))
    await make_stock(db, u, tomato, 200)   # 有番茄, 没蒜

    recs = await recommend_recipes(db, u, max_missing=2)
    assert len(recs) == 1
    assert recs[0]["missing_count"] == 1
    assert recs[0]["missing_ingredients"][0]["name"] == "garlic"


async def test_too_many_missing_filtered(db):
    """缺料数 > max_missing → 过滤掉。"""
    u = await make_user(db)
    a = await make_ingredient(db, "a")
    b = await make_ingredient(db, "b")
    c = await make_ingredient(db, "c")
    await make_variant(db, (a, 100), (b, 100), (c, 100))
    await make_stock(db, u, a, 200)        # 只有 a, 缺 b、c 两样... 设 max=1

    recs = await recommend_recipes(db, u, max_missing=1)
    assert recs == []                       # 缺 2 样 > 1, 过滤


async def test_sorted_by_missing_count(db):
    """多个菜谱按缺料数升序: 全齐的在缺料的前面。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    egg = await make_ingredient(db, "egg")
    garlic = await make_ingredient(db, "garlic")
    await make_stock(db, u, tomato, 200)
    await make_stock(db, u, egg, 100)
    # 菜谱1: 全齐(番茄+蛋)
    await make_variant(db, (tomato, 100), (egg, 50))
    # 菜谱2: 缺蒜
    await make_variant(db, (tomato, 100), (garlic, 10))

    recs = await recommend_recipes(db, u, max_missing=2)
    assert len(recs) == 2
    assert recs[0]["missing_count"] == 0    # 全齐的在前
    assert recs[1]["missing_count"] == 1


async def test_only_visible_recipes(db):
    """别人的私有菜谱不进推荐(可见性)。"""
    u = await make_user(db)
    from app.users.models import User
    other = User(clerk_user_id="other_rec_user")
    db.add(other)
    await db.flush()
    tomato = await make_ingredient(db, "tomato")
    await make_stock(db, u, tomato, 200)
    # 别人的私有菜谱(全齐, 但不该出现)
    await make_variant(db, (tomato, 100), visibility="private")
    # make_variant 的私有 recipe created_by 是 NULL, 但为测可见性, 手动设成 other
    from sqlalchemy import update

    from app.recipes.models import Recipe
    await db.execute(
        update(Recipe).where(Recipe.visibility == "private").values(created_by_user_id=other.id)
    )
    await db.flush()

    recs = await recommend_recipes(db, u, max_missing=2)
    assert recs == []                       # 别人的私有, 看不见

async def test_partial_stock_counts_as_short(db):
    """库存有该食材但量不够 → status=partial, 计入 missing_count。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    egg = await make_ingredient(db, "egg")
    await make_variant(db, (tomato, 100), (egg, 50))
    await make_stock(db, u, tomato, 200)   # 番茄够
    await make_stock(db, u, egg, 20)       # 蛋不够(需 50 只有 20)

    recs = await recommend_recipes(db, u, max_missing=2)
    assert len(recs) == 1
    rec = recs[0]
    assert rec["missing_count"] == 1                       # 蛋不够, 算缺 1
    # 完整清单三态: 番茄 have, 蛋 partial
    by_name = {i["name"]: i["status"] for i in rec["ingredients"]}
    assert by_name["tomato"] == "have"
    assert by_name["egg"] == "partial"
    # 向后兼容: missing_ingredients 只含"完全没有"的, 蛋是 partial 不在其中
    assert rec["missing_ingredients"] == []


async def test_ingredients_full_list_returned(db):
    """返回完整食材清单(有的+没有的都在 ingredients 里)。"""
    u = await make_user(db)
    tomato = await make_ingredient(db, "tomato")
    garlic = await make_ingredient(db, "garlic")
    await make_variant(db, (tomato, 100), (garlic, 10))
    await make_stock(db, u, tomato, 200)   # 有番茄, 没蒜

    recs = await recommend_recipes(db, u, max_missing=2)
    rec = recs[0]
    assert len(rec["ingredients"]) == 2                    # 完整清单 2 样
    by_name = {i["name"]: i["status"] for i in rec["ingredients"]}
    assert by_name["tomato"] == "have"
    assert by_name["garlic"] == "missing"