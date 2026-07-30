# tests/ai/test_generate_recipe.py
from decimal import Decimal

import pytest
from sqlalchemy import func, select

import app.ai.services as svc
from app.ai.client import AiError, AiResult
from app.ai.models import AiGenerationLog
from app.ai.services import (
    EmptyInventoryError,
    RecipeValidationError,
    generate_recipe,
)
from app.recipes.models import Recipe, RecipeVariant
from tests.factories import make_ingredient, make_stock, make_user

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _fake_result(ingredient_id, name="AI 番茄菜", amount=200):
    """构造一个假的 AI 返回(不调真 API)。"""
    return AiResult(
        tool_input={
            "name": name,
            "description": "AI 生成",
            "cuisine": "chinese",
            "servings": 2,
            "instructions": "step 1\nstep 2",
            "ingredients": [{"ingredient_id": ingredient_id, "amount_grams": amount}],
        },
        input_tokens=1500,
        output_tokens=600,
    )


async def _seed_inventory(db, user):
    """给用户库存里放一个食材, 返回该食材。"""
    tomato = await make_ingredient(db, "tomato", visibility="global")
    await make_stock(db, user, tomato, 500)
    return tomato


async def test_generate_success_persists_recipe_and_log(db, monkeypatch):
    """成功: 建出 ai_generated 菜谱 + 一条 success 日志, 两向 FK 互链。"""
    user = await make_user(db)
    tomato = await _seed_inventory(db, user)

    async def fake_raw(prompt):
        return _fake_result(tomato.id)
    monkeypatch.setattr(svc, "generate_recipe_raw", fake_raw)

    recipe = await generate_recipe(db, user, free_text="随便")

    assert recipe.source == "ai_generated"
    assert recipe.visibility == "private"
    assert recipe.created_by_user_id == user.id
    assert recipe.ai_generation_log_id is not None

    log = (await db.execute(select(AiGenerationLog))).scalar_one()
    assert log.status == "success"
    assert log.created_recipe_id == recipe.id      # 反向链
    assert recipe.ai_generation_log_id == log.id   # 正向链
    assert log.input_tokens == 1500 and log.output_tokens == 600


async def test_hallucinated_id_rejected_and_logged(db, monkeypatch):
    """AI 幻觉出清单外 id → 校验拦截, 不建菜谱, 记 failed 日志。"""
    user = await make_user(db)
    await _seed_inventory(db, user)      # 库存只有 tomato

    async def fake_raw(prompt):
        return _fake_result(999999)      # 清单外的 id
    monkeypatch.setattr(svc, "generate_recipe_raw", fake_raw)

    with pytest.raises(RecipeValidationError):
        await generate_recipe(db, user)

    # 没有菜谱被建
    assert (await db.execute(select(func.count()).select_from(Recipe))).scalar() == 0
    # 但有一条 failed 日志(留痕)
    log = (await db.execute(select(AiGenerationLog))).scalar_one()
    assert log.status == "failed"
    assert log.created_recipe_id is None
    assert "清单外" in log.error_message


async def test_ai_error_logged_as_failed(db, monkeypatch):
    """AI 调用本身失败(超时/拒答) → 记 failed 日志。"""
    user = await make_user(db)
    await _seed_inventory(db, user)

    async def fake_raw(prompt):
        raise AiError("模型未按工具返回")
    monkeypatch.setattr(svc, "generate_recipe_raw", fake_raw)

    with pytest.raises(AiError):
        await generate_recipe(db, user)

    assert (await db.execute(select(func.count()).select_from(Recipe))).scalar() == 0
    log = (await db.execute(select(AiGenerationLog))).scalar_one()
    assert log.status == "failed"


async def test_empty_inventory_raises_no_log(db, monkeypatch):
    """库存为空 → 直接报错, 不调 AI、不记日志(没发生 AI 调用)。"""
    user = await make_user(db)   # 没放库存

    called = False
    async def fake_raw(prompt):
        nonlocal called
        called = True
        return _fake_result(1)
    monkeypatch.setattr(svc, "generate_recipe_raw", fake_raw)

    with pytest.raises(EmptyInventoryError):
        await generate_recipe(db, user)
    assert called is False        # 没调 AI
    assert (await db.execute(select(func.count()).select_from(AiGenerationLog))).scalar() == 0


async def test_generated_recipe_has_nutrition(db, monkeypatch):
    """生成的菜谱营养被聚合(复用 compute_variant_nutrition)。"""
    user = await make_user(db)
    tomato = await make_ingredient(db, "tomato", visibility="global")
    tomato.per_100g_calories = Decimal("20")
    await make_stock(db, user, tomato, 500)
    await db.flush()

    async def fake_raw(prompt):
        return _fake_result(tomato.id, amount=200)   # 200g × 20/100 = 40 cal
    monkeypatch.setattr(svc, "generate_recipe_raw", fake_raw)

    recipe = await generate_recipe(db, user)
    variant = (await db.execute(
        select(RecipeVariant).where(RecipeVariant.recipe_id == recipe.id)
    )).scalar_one()
    assert variant.total_calories == Decimal("40.00")