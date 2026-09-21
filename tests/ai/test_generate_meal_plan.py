# tests/ai/test_generate_meal_plan.py
from datetime import date

import pytest
from sqlalchemy import func, select

import app.ai.services as svc
from app.ai.client import AiError, AiResult
from app.ai.models import AiGenerationLog
from app.ai.services import (
    EmptyRecipeCatalogError,
    RecipeValidationError,
    generate_meal_plan,
)
from app.meal_plans.models import MealPlan, MealPlanEntry
from tests.factories import make_ingredient, make_user, make_variant

pytestmark = pytest.mark.asyncio(loop_scope="session")

START = date(2026, 8, 10)


def _fake_plan(variant_id, days=2):
    """假 AI 返回: 每天 lunch+dinner 都排同一个 variant。"""
    entries = []
    for d in range(days):
        for m in ("lunch", "dinner"):
            entries.append({
                "day_offset": d, "meal_type": m,
                "recipe_variant_id": variant_id, "servings": 1,
            })
    return AiResult(tool_input={"entries": entries}, input_tokens=800, output_tokens=400)


async def _seed_recipe(db):
    tomato = await make_ingredient(db, "tomato", visibility="global")
    v = await make_variant(db, (tomato, 100))   # 建可见菜谱+variant
    return v


async def test_generate_plan_returns_draft_no_persist(db, monkeypatch):
    """成功: 返回草稿(不落库) + 记 success 日志(kind=meal_plan)。
    阶段A: 生成只出草稿, 计划/entries 在用户确认(commit)时才建。
    """
    u = await make_user(db)
    v = await _seed_recipe(db)

    async def fake_raw(prompt):
        return _fake_plan(v.id, days=2)
    monkeypatch.setattr(svc, "generate_meal_plan_raw", fake_raw)

    draft = await generate_meal_plan(db, u, start_date=START, days=2, meals=["lunch", "dinner"])

    # 草稿形状
    assert draft["start_date"] == START
    assert draft["days"] == 2
    assert len(draft["entries"]) == 4              # 2 天 × 2 餐
    e0 = draft["entries"][0]
    assert e0["recipe_variant_id"] == v.id
    assert "recipe_name" in e0                     # 带菜名供前端预览

    # 不落库: 没有 MealPlan / entries
    assert (await db.execute(select(func.count()).select_from(MealPlan))).scalar() == 0
    assert (await db.execute(select(func.count()).select_from(MealPlanEntry))).scalar() == 0

    # 记了 success 日志
    log = (await db.execute(select(AiGenerationLog))).scalar_one()
    assert log.status == "success" and log.kind == "meal_plan"


async def test_hallucinated_variant_rejected(db, monkeypatch):
    """AI 挑了清单外 variant_id → 拦截, 不建计划, 记 failed(kind=meal_plan)。"""
    u = await make_user(db)
    await _seed_recipe(db)

    async def fake_raw(prompt):
        return _fake_plan(999999, days=1)
    monkeypatch.setattr(svc, "generate_meal_plan_raw", fake_raw)

    with pytest.raises(RecipeValidationError):
        await generate_meal_plan(db, u, start_date=START, days=1)

    assert (await db.execute(select(func.count()).select_from(MealPlan))).scalar() == 0
    log = (await db.execute(select(AiGenerationLog))).scalar_one()
    assert log.status == "failed" and log.kind == "meal_plan"


async def test_day_offset_out_of_range_rejected(db, monkeypatch):
    """day_offset 越界 → 拦截。"""
    u = await make_user(db)
    v = await _seed_recipe(db)

    async def fake_raw(prompt):
        return AiResult(tool_input={"entries": [
            {"day_offset": 5, "meal_type": "lunch", "recipe_variant_id": v.id}
        ]}, input_tokens=1, output_tokens=1)
    monkeypatch.setattr(svc, "generate_meal_plan_raw", fake_raw)

    with pytest.raises(RecipeValidationError):
        await generate_meal_plan(db, u, start_date=START, days=2)   # 只 0..1


async def test_empty_catalog_raises(db, monkeypatch):
    """无可用菜谱 → 报错, 不调 AI。"""
    u = await make_user(db)   # 没建任何菜谱

    called = False
    async def fake_raw(prompt):
        nonlocal called
        called = True
        return _fake_plan(1)
    monkeypatch.setattr(svc, "generate_meal_plan_raw", fake_raw)

    with pytest.raises(EmptyRecipeCatalogError):
        await generate_meal_plan(db, u, start_date=START)
    assert called is False


async def test_ai_error_logged_failed(db, monkeypatch):
    """AI 调用失败 → 记 failed(kind=meal_plan)。"""
    u = await make_user(db)
    await _seed_recipe(db)

    async def fake_raw(prompt):
        raise AiError("超时")
    monkeypatch.setattr(svc, "generate_meal_plan_raw", fake_raw)

    with pytest.raises(AiError):
        await generate_meal_plan(db, u, start_date=START)
    log = (await db.execute(select(AiGenerationLog))).scalar_one()
    assert log.status == "failed" and log.kind == "meal_plan"