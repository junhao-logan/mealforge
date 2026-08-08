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


async def test_generate_plan_success(db, monkeypatch):
    """成功: 建 ai_generated 计划 + entries + success 日志(kind=meal_plan)。"""
    u = await make_user(db)
    v = await _seed_recipe(db)

    async def fake_raw(prompt):
        return _fake_plan(v.id, days=2)
    monkeypatch.setattr(svc, "generate_meal_plan_raw", fake_raw)

    plan = await generate_meal_plan(db, u, start_date=START, days=2, meals=["lunch", "dinner"])

    assert plan.plan_type == "ai_generated"
    assert plan.start_date == START
    assert plan.end_date == date(2026, 8, 11)     # 2 天
    assert plan.ai_generation_log_id is not None

    n_entries = (await db.execute(
        select(func.count()).select_from(MealPlanEntry).where(
            MealPlanEntry.meal_plan_id == plan.id)
    )).scalar()
    assert n_entries == 4                          # 2 天 × 2 餐

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