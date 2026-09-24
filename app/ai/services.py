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

from app.ai.client import AiError, AiResult, generate_meal_plan_raw, generate_recipe_raw
from app.ai.models import AiGenerationLog
from app.ai.prompts import build_meal_plan_message, build_user_message
from app.core.config import get_settings
from app.ingredients.access import normalize_name, visible_to
from app.ingredients.models import Ingredient
from app.inventory.models import InventoryItem
from app.meal_plans.schemas import AMOUNT_MAX
from app.recipes.models import Recipe, RecipeIngredient, RecipeVariant
from app.recipes.services import (
    compute_variant_nutrition,
    recipe_visible_to,
    resolve_quantity,
)


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
        .options(
            selectinload(Recipe.variants)
            .selectinload(RecipeVariant.ingredients)
            .selectinload(RecipeIngredient.ingredient)   # 响应里带食材名
        )
    )).scalar_one()
    return loaded


def _num(v):
    return None if v is None else Decimal(str(v))


async def _dedupe_or_create_ingredient(db, user, name: str, per100g: dict | None) -> Ingredient:
    """新食材: 先按规范化名去重(全局或本人私有)。命中 → 复用(用库里准确营养);
    没有 → 新建(克本位 + AI 估算营养, source=ai_generated, private)。不 commit。"""
    norm = normalize_name(name)
    ing = (await db.execute(
        select(Ingredient).where(
            Ingredient.name_normalized == norm, visible_to(user.id),
        ).order_by(Ingredient.id).limit(1)
    )).scalar_one_or_none()
    if ing is not None:
        return ing                         # 命中: 用库里的准确营养, 不用 AI 估

    p = per100g or {}
    ing = Ingredient(
        name=name.strip(), name_normalized=norm,
        source="ai_generated", visibility="private", created_by_user_id=user.id,
        default_unit="g", grams_per_unit=Decimal("1"),
        nutrition_basis_unit="g", nutrition_basis_amount=Decimal("100"),
        per_100g_calories=_num(p.get("calories")),
        per_100g_protein=_num(p.get("protein")),
        per_100g_carbs=_num(p.get("carbs")),
        per_100g_fat=_num(p.get("fat")),
    )
    db.add(ing)
    await db.flush()
    return ing


async def persist_new_recipe(db, user, nr: dict) -> int:
    """把一份 AI 现编菜谱落库(用户确认时) → 返回新 recipe_variant_id。
    配料: ingredient_id 直接用; new_name 按名去重(命中复用, 否则新建)。不 commit。"""
    resolved = []
    for ln in nr["ingredients"]:
        iid = ln.get("ingredient_id")
        if iid is not None:
            # 只能引用自己看得见的食材(I11), 与 palette 口径一致
            ing = (await db.execute(
                select(Ingredient).where(Ingredient.id == iid, visible_to(user.id))
            )).scalar_one_or_none()
            if ing is None:
                raise RecipeValidationError(f"配料引用了不存在的食材 id: {iid}")
        else:
            ing = await _dedupe_or_create_ingredient(
                db, user, ln["new_name"], ln.get("per100g"))
        amount = Decimal(str(ln["amount"]))
        unit = ing.nutrition_basis_unit or "g"
        resolved.append((ing, amount, unit))

    recipe = Recipe(
        name=nr["name"], cuisine=nr.get("cuisine"),
        source="ai_generated", visibility="private", created_by_user_id=user.id,
    )
    variant = RecipeVariant(
        name="AI", instructions=nr["instructions"],
        # servings 是整数列: 0.5 之类四舍五入, 至少 1 份(int() 会把 0.5 截成 0)
        servings=max(1, round(float(nr.get("servings") or 1))),
    )
    for ing, amount, unit in resolved:
        qty = resolve_quantity(ing, amount, unit)
        ri = RecipeIngredient(
            ingredient_id=ing.id, quantity_grams=qty,
            input_amount=amount, input_unit=unit,
        )
        ri.ingredient = ing               # 供营养聚合读 per-基准 营养
        variant.ingredients.append(ri)
    compute_variant_nutrition(variant)
    variant.recipe = recipe
    db.add(recipe)
    await db.flush()
    return variant.id


async def _persist_failure_log(
    db: AsyncSession, user, prompt: str, model: str, error: str, raw: dict | None,
    kind: str = "recipe",
) -> None:
    """失败路径: 独立事务记一条 failed 日志(留痕 debug)。"""
    log = AiGenerationLog(
        user_id=user.id, kind=kind, status="failed", model=model,
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
    model = get_settings().gemini_model

    try:
        result = await generate_recipe_raw(prompt)   # 调 AI(测试 mock)
        _validate(result.tool_input, catalog_ids)     # 防幻觉硬校验(在建库前)
        return await _persist_success(db, user, result, prompt, model)
    except (AiError, RecipeValidationError) as e:
        # 校验先于持久化, 失败时尚未建任何菜谱行 → 无需回滚, 只记 failed 日志
        raw = getattr(e, "raw", None)
        await _persist_failure_log(db, user, prompt, model, str(e), raw)
        raise

class EmptyRecipeCatalogError(Exception):
    """没有可用菜谱做法, 无法排周计划。"""


async def _variant_catalog(db: AsyncSession, user_id) -> list[dict]:
    """grounding 数据: 用户可见菜谱的所有 variant + 主料名(供 AI 挑选排布)。"""
    rows = (await db.execute(
        select(
            RecipeVariant.id, Recipe.name, RecipeVariant.name,
            Ingredient.name, RecipeIngredient.ingredient_id,
        )
        .join(Recipe, Recipe.id == RecipeVariant.recipe_id)
        .join(RecipeIngredient, RecipeIngredient.recipe_variant_id == RecipeVariant.id)
        .join(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
        .where(recipe_visible_to(user_id))
    )).all()

    catalog: dict[int, dict] = {}
    for v_id, r_name, v_name, ing_name, ing_id in rows:
        c = catalog.setdefault(v_id, {
            "variant_id": v_id, "recipe_name": r_name,
            "variant_name": v_name, "ingredients": [], "ingredient_ids": [],
        })
        c["ingredients"].append(ing_name)
        c["ingredient_ids"].append(ing_id)
    return list(catalog.values())


async def _inventory_ingredient_ids(db: AsyncSession, user_id) -> set[int]:
    """当前有货(quantity_grams>0)的食材 id 集合 —— 供"只用库存"过滤。"""
    rows = (await db.execute(
        select(InventoryItem.ingredient_id)
        .where(InventoryItem.user_id == user_id, InventoryItem.quantity_grams > 0)
        .distinct()
    )).all()
    return {r[0] for r in rows}


def _validate_plan(tool_input: dict, catalog_ids: set[int], days: int,
                   meals: set[str], *, palette_ids: set[int] | None = None,
                   allow_new: bool = False) -> list[dict]:
    """防幻觉硬校验: 每条 entry 用已有 variant_id 或(allow_new 时)新编 new_recipe;
    day_offset/meal_type 合法; new_recipe 配料要么引用 palette 里的 id, 要么给 new_name。"""
    palette_ids = palette_ids or set()
    entries = tool_input.get("entries") or []
    if not entries:
        raise RecipeValidationError("AI 未返回任何餐次", raw=tool_input)
    for e in entries:
        if not (0 <= e["day_offset"] < days):
            raise RecipeValidationError(f"day_offset 越界: {e['day_offset']}", raw=tool_input)
        if e["meal_type"] not in meals:
            raise RecipeValidationError(f"非法餐段: {e['meal_type']}", raw=tool_input)

        nr = e.get("new_recipe")
        if nr is not None:
            if not allow_new:
                raise RecipeValidationError("当前不允许现编新菜谱", raw=tool_input)
            if not nr.get("name") or not nr.get("instructions"):
                raise RecipeValidationError("new_recipe 缺 name/instructions", raw=tool_input)
            lines = nr.get("ingredients") or []
            if not lines:
                raise RecipeValidationError("new_recipe 无配料", raw=tool_input)
            for ln in lines:
                iid = ln.get("ingredient_id")
                if iid is not None and iid not in palette_ids:
                    raise RecipeValidationError(
                        f"new_recipe 引用了清单外的食材 id: {iid}", raw=tool_input
                    )
                name = (ln.get("new_name") or "").strip()
                if iid is None and not name:
                    raise RecipeValidationError(
                        "配料无 ingredient_id 也无 new_name", raw=tool_input)
                if len(name) > 100:
                    raise RecipeValidationError("new_name 过长", raw=tool_input)
                # 与确认接口(NewRecipeIngredient)同一上限: 能预览出来的草稿就一定能确认
                if not ln.get("amount") or not 0 < float(ln["amount"]) <= AMOUNT_MAX:
                    raise RecipeValidationError("amount 必须在 (0, 100000] 内", raw=tool_input)
            continue

        vid = e.get("recipe_variant_id")
        if vid is None:
            raise RecipeValidationError(
                "entry 无 recipe_variant_id 也无 new_recipe", raw=tool_input)
        if vid not in catalog_ids:
            raise RecipeValidationError(
                f"引用了清单外的做法 id: {vid}", raw=tool_input)
    return entries


async def _ingredient_palette(db: AsyncSession, user_id, *, only_ids=None) -> list[dict]:
    """现编新菜谱的 grounding: 用户可见食材(全局或本人私有)的 id + 名字 + 规范单位。
    only_ids 给定时只取这些(用于"只用库存"—— 限定在库存食材里现编)。
    上限 80 条(控 prompt 体积); 先放自己建的、再按名字排, 截断结果稳定可复现。"""
    stmt = (
        select(Ingredient.id, Ingredient.name, Ingredient.nutrition_basis_unit)
        .where(visible_to(user_id))
        .order_by((Ingredient.created_by_user_id == user_id).desc(), Ingredient.name)
    )
    if only_ids is not None:
        if not only_ids:
            return []
        stmt = stmt.where(Ingredient.id.in_(only_ids))
    rows = (await db.execute(stmt.limit(80))).all()
    return [{"id": r[0], "name": r[1], "unit": r[2] or "g"} for r in rows]


async def _log_plan_success(db, user, result, prompt, model) -> None:
    """AI 调用成功 → 记一条 meal_plan 成功日志(审计)。
    注意: 生成阶段只出草稿、不建计划/entries —— 计划在用户确认(commit)时才落库。
    """
    ti = result.tool_input
    db.add(AiGenerationLog(
        user_id=user.id, kind="meal_plan", status="success", model=model,
        prompt=prompt, raw_response=json.dumps(ti, ensure_ascii=False),
        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
    ))
    await db.commit()


async def generate_meal_plan(
    db: AsyncSession, user, *,
    start_date, days: int = 7,
    meals: list[str] | None = None,
    free_text: str | None = None,
    ingredient_source: str = "any",
    recipe_source: str = "existing",
    language: str | None = None,
):
    """AI 排 N 天计划 → 返回**草稿**(不落库)。

    · recipe_source='existing': 只用已有菜谱(阶段A)
    · recipe_source='new': 可混用已有 + 现编新菜谱/新食材(阶段B), 确认后才入库
    · ingredient_source='inventory': 只用库存(已有做法只留库存能做的; 现编只用库存食材), 不硬凑
    · ingredient_source='any': 不限(缺料后续采购补齐)
    返回草稿, entries 每条: 已有 → recipe_variant_id; 现编 → is_new + new_recipe。
    """
    meals = meals or ["lunch", "dinner"]
    allow_new = recipe_source == "new"
    inventory_only = ingredient_source == "inventory"
    stock = await _inventory_ingredient_ids(db, user.id) if inventory_only else None

    catalog = await _variant_catalog(db, user.id)
    if inventory_only:
        catalog = [
            c for c in catalog
            if c["ingredient_ids"] and set(c["ingredient_ids"]) <= stock
        ]

    # 现编需要食材调色板(库存模式限定库存食材)
    palette = await _ingredient_palette(db, user.id, only_ids=stock) if allow_new else []
    palette_ids = {p["id"] for p in palette}

    # 无已有做法 且 不允许现编(或现编但也没食材) → 无从生成
    if not catalog and not (allow_new and palette):
        raise EmptyRecipeCatalogError(
            "没有可用菜谱; 换'允许 AI 新编'或先加点菜谱/库存" if not allow_new
            else "库存里没有可用食材, 先加点库存或改用'允许采购'"
        )

    by_id = {c["variant_id"]: c for c in catalog}
    catalog_ids = set(by_id)
    prompt = build_meal_plan_message(
        catalog, days=days, meals=meals, free_text=free_text,
        inventory_only=inventory_only, language=language,
        allow_new=allow_new, ingredients=palette,
    )
    model = get_settings().gemini_model

    try:
        result = await generate_meal_plan_raw(prompt)
        entries = _validate_plan(
            result.tool_input, catalog_ids, days, set(meals),
            palette_ids=palette_ids, allow_new=allow_new,
        )
        await _log_plan_success(db, user, result, prompt, model)
    except (AiError, RecipeValidationError) as e:
        raw = getattr(e, "raw", None)
        await _persist_failure_log(
            db, user, prompt, model, str(e), raw, kind="meal_plan"
        )
        raise

    # 组装草稿(不落库)
    draft_entries = []
    for e in entries:
        base = {
            "day_offset": e["day_offset"],
            "meal_type": e["meal_type"],
            "servings": Decimal(str(e.get("servings") or 1)),
        }
        nr = e.get("new_recipe")
        if nr is not None:
            base.update({
                "is_new": True,
                "recipe_name": nr.get("name", ""),
                "new_recipe": nr,
            })
        else:
            c = by_id.get(e["recipe_variant_id"], {})
            base.update({
                "is_new": False,
                "recipe_variant_id": e["recipe_variant_id"],
                "recipe_name": c.get("recipe_name", ""),
                "variant_name": c.get("variant_name"),
            })
        draft_entries.append(base)

    return {
        "start_date": start_date,
        "days": days,
        "meals": meals,
        "entries": draft_entries,
    }