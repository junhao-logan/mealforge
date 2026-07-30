# app/ai/services.py
"""AI 菜谱生成 service —— 串起 grounding / 调用 / 校验 / 落库 / 记日志。

事务策略(决策 a): 成功时菜谱 + 日志同事务提交(两向 FK 互链); 失败时回滚
菜谱、单独提交一条 failed 日志(失败也留痕, 用于 debug)。
"""
from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.client import AiError, AiResult, generate_recipe_raw
from app.ai.models import AiGenerationLog
from app.ai.prompts import build_user_message
from app.core.config import get_settings
from app.ingredients.models import Ingredient
from app.inventory.models import InventoryItem
from app.recipes.models import Recipe, RecipeIngredient, RecipeVariant
from app.recipes.services import compute_variant_nutrition


class EmptyInventoryError(Exception):
    """库存为空, 无法从库存生成。"""


class RecipeValidationError(Exception):
    """AI 输出校验失败(幻觉出清单外食材 / 无食材等)。携带原始输出供记录。"""
    def __init__(self, message: str, raw: dict | None = None):
        super().__init__(message)
        self.raw = raw


async def _inventory_catalog(db: AsyncSession, user_id) -> list[dict]:
    """grounding 数据: 用户库存里现有(>0)的去重食材, 只取 id/name/category。"""
    stmt = (
        select(Ingredient.id, Ingredient.name, Ingredient.category)
        .join(InventoryItem, InventoryItem.ingredient_id == Ingredient.id)
        .where(InventoryItem.user_id == user_id, InventoryItem.quantity_grams > 0)
        .distinct()
    )
    rows = (await db.execute(stmt)).all()
    return [{"id": r.id, "name": r.name, "category": r.category} for r in rows]


def _validate(tool_input: dict, catalog_ids: set[int]) -> list[dict]:
    """防幻觉硬校验: AI 引用的每个 ingredient_id 必须在可用清单内。"""
    items = tool_input.get("ingredients") or []
    if not items:
        raise RecipeValidationError("AI 未返回任何食材", raw=tool_input)
    bad = [it["ingredient_id"] for it in items if it["ingredient_id"] not in catalog_ids]
    if bad:
        raise RecipeValidationError(
            f"AI 引用了清单外的食材 id: {bad}", raw=tool_input
        )
    return items


async def _persist_success(
    db: AsyncSession, user, result: AiResult, prompt: str, model: str
) -> Recipe:
    """成功路径: 日志 + 菜谱同事务, 两向 FK 互链, 一次 commit。"""
    ti = result.tool_input

    # 1. 先建日志拿 id
    log = AiGenerationLog(
        user_id=user.id, kind="recipe", status="success", model=model,
        prompt=prompt,
        raw_response=json.dumps(ti, ensure_ascii=False),
        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
    )
    db.add(log)
    await db.flush()

    # 2. 建菜谱(source=ai_generated, 私有归属当前用户, 关联日志)
    recipe = Recipe(
        name=ti["name"],
        description=ti.get("description"),
        cuisine=ti.get("cuisine"),
        source="ai_generated",
        visibility="private",
        created_by_user_id=user.id,
        ai_generation_log_id=log.id,
    )
    variant = RecipeVariant(
        name="AI 生成",
        instructions=ti["instructions"],
        cooking_time_minutes=ti.get("cooking_time_minutes"),
        difficulty=ti.get("difficulty"),
        servings=ti.get("servings") or 1,
    )

    # 3. 配料(id 已校验存在); AI 直接给克数 → input 即克
    ing_ids = [it["ingredient_id"] for it in ti["ingredients"]]
    ings = (await db.execute(
        select(Ingredient).where(Ingredient.id.in_(ing_ids))
    )).scalars().all()
    ing_map = {i.id: i for i in ings}
    for it in ti["ingredients"]:
        ing = ing_map[it["ingredient_id"]]
        grams = Decimal(str(it["amount_grams"]))
        ri = RecipeIngredient(
            ingredient_id=ing.id, quantity_grams=grams,
            input_amount=grams, input_unit="g",
        )
        ri.ingredient = ing         # 供营养聚合读 per-100g
        variant.ingredients.append(ri)

    compute_variant_nutrition(variant)     # 复用现有聚合(D6)
    variant.recipe = recipe

    db.add(recipe)
    await db.flush()
    log.created_recipe_id = recipe.id      # 回填反向链
    await db.commit()

    # 重载完整对象(含 variant/ingredients)供返回
    loaded = (await db.execute(
        select(Recipe)
        .where(Recipe.id == recipe.id)
        .options(selectinload(Recipe.variants).selectinload(RecipeVariant.ingredients))
    )).scalar_one()
    return loaded


async def _persist_failure_log(
    db: AsyncSession, user, prompt: str, model: str, error: str, raw: dict | None
) -> None:
    """失败路径: 独立事务记一条 failed 日志(留痕 debug)。"""
    log = AiGenerationLog(
        user_id=user.id, kind="recipe", status="failed", model=model,
        prompt=prompt,
        raw_response=json.dumps(raw, ensure_ascii=False) if raw else None,
        error_message=error,
    )
    db.add(log)
    await db.commit()


async def generate_recipe(
    db: AsyncSession, user, *,
    free_text: str | None = None,
    cuisine: str | None = None,
    goal: str | None = None,
    servings: int | None = None,
) -> Recipe:
    """从用户库存生成一个菜谱(第一版)。

    扩展点: 未来"按要求从全库选""网络热门"只需替换 catalog 来源 / 放开校验,
    主流程(拼 prompt→调 AI→校验→落库→记日志)不变。
    """
    catalog = await _inventory_catalog(db, user.id)
    if not catalog:
        raise EmptyInventoryError("库存为空, 无法从库存生成菜谱")

    catalog_ids = {c["id"] for c in catalog}
    prompt = build_user_message(
        catalog, free_text=free_text, cuisine=cuisine,
        goal=goal, servings=servings,
    )
    model = get_settings().anthropic_model

    try:
        result = await generate_recipe_raw(prompt)   # 调 AI(测试 mock)
        _validate(result.tool_input, catalog_ids)     # 防幻觉硬校验(在建库前)
        return await _persist_success(db, user, result, prompt, model)
    except (AiError, RecipeValidationError) as e:
        # 校验先于持久化, 失败时尚未建任何菜谱行 → 无需回滚, 只记 failed 日志
        raw = getattr(e, "raw", None)
        await _persist_failure_log(db, user, prompt, model, str(e), raw)
        raise