from __future__ import annotations

from datetime import UTC
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredients.models import Ingredient
from app.inventory.models import InventoryItem
from app.recipes.models import Recipe, RecipeIngredient, RecipeVariant


async def resolve_grams(
    db: AsyncSession, ingredient: Ingredient, input_amount: Decimal, input_unit: str
) -> Decimal:
    """D5: 把'用户单位+数量'换算成克。单位限 'g' 或该食材 default_unit(D5a)。"""
    if input_unit == "g":
        return input_amount  # 克 → 克, ×1
    if input_unit == ingredient.default_unit:
        return input_amount * ingredient.grams_per_unit
    # 其他单位 MVP 不支持(多单位换算表留 Phase 2)
    raise HTTPException(
        status_code=422,
        detail=f"食材 '{ingredient.name}' 只支持单位 'g' 或 '{ingredient.default_unit}',"
               f" 收到 '{input_unit}'",
    )


def compute_variant_nutrition(variant: RecipeVariant) -> None:
    """D6: 聚合配料营养,写回 variant 的缓存列。原地修改,不返回。

    前提: variant.ingredients 已加载, 且每条 .ingredient 关系已加载。
    NULL 传播: 任一配料的某营养是 NULL(unknown), 该营养总和也设 NULL(D2 延续,
    不把 unknown 当 0)。
    """
    total_grams = Decimal("0")
    # 四宏量分别累加; None 标记表示遇到了 unknown, 该项最终为 NULL
    sums: dict[str, Decimal | None] = {
        "calories": Decimal("0"), "protein": Decimal("0"),
        "carbs": Decimal("0"), "fat": Decimal("0"),
    }
    # per-100g 营养字段名映射
    fields = {
        "calories": "per_100g_calories", "protein": "per_100g_protein",
        "carbs": "per_100g_carbs", "fat": "per_100g_fat",
    }

    for ri in variant.ingredients:
        grams = ri.quantity_grams
        total_grams += grams
        ing = ri.ingredient
        for key, col in fields.items():
            if sums[key] is None:
                continue  # 已被标记 unknown, 跳过
            per_100g = getattr(ing, col)
            if per_100g is None:
                sums[key] = None  # 这条食材该营养未知 → 整道菜该项 unknown
            else:
                sums[key] += per_100g * grams / Decimal("100")

    variant.total_grams = total_grams
    variant.total_calories = sums["calories"]
    variant.total_protein_g = sums["protein"]
    variant.total_carbs_g = sums["carbs"]
    variant.total_fat_g = sums["fat"]
    # nutrition_computed_at 用 DB 时间, 这里用 Python now 也可; 简单起见标记已算
    from datetime import datetime
    variant.nutrition_computed_at = datetime.now(UTC)

async def recommend_recipes(
    db: AsyncSession, user, *, max_missing: int = 2
) -> list[dict]:
    """反向推荐(功能B): 库存能做哪些【已有可见菜谱的做法】, 宽松匹配。

    以 variant 为单位, 只看"有没有该食材"(不看克数)。返回按缺料数升序:
    全齐的最前, 缺 ≤max_missing 样的列出缺啥, 缺太多的过滤掉。

    无 N+1: 几条固定查询(与菜谱数无关)+ 内存集合运算, 对齐 compute_shortfall 思路。
    """
    # 1. 我库存有哪些食材 id(一个集合, 只看种类不看量)
    stock_stmt = (
        select(InventoryItem.ingredient_id)
        .where(InventoryItem.user_id == user.id, InventoryItem.quantity_grams > 0)
        .distinct()
    )
    stock_ids = {r[0] for r in (await db.execute(stock_stmt)).all()}

    # 2. 一次拉全: 可见菜谱的 variant + 其每条配料(id/名字)
    #    可见性(I11): global 或自己建的
    rows_stmt = (
        select(
            Recipe.id, Recipe.name,
            RecipeVariant.id, RecipeVariant.name,
            RecipeIngredient.ingredient_id, Ingredient.name,
        )
        .join(RecipeVariant, RecipeVariant.recipe_id == Recipe.id)
        .join(RecipeIngredient, RecipeIngredient.recipe_variant_id == RecipeVariant.id)
        .join(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
        .where(
            or_(
                Recipe.visibility == "global",
                Recipe.created_by_user_id == user.id,
            )
        )
    )
    rows = (await db.execute(rows_stmt)).all()

    # 3. 内存聚合: 按 variant 归组, 算缺料
    variants: dict[int, dict] = {}
    for r_id, r_name, v_id, v_name, ing_id, ing_name in rows:
        v = variants.setdefault(v_id, {
            "recipe_id": r_id, "recipe_name": r_name,
            "variant_id": v_id, "variant_name": v_name,
            "missing_ingredients": [],
        })
        if ing_id not in stock_ids:
            v["missing_ingredients"].append({"id": ing_id, "name": ing_name})

    # 4. 过滤 + 排序: 缺 ≤max_missing 才留; 缺得越少越前, 同缺数按 recipe_id 定序
    result = []
    for v in variants.values():
        miss = v["missing_ingredients"]
        if len(miss) <= max_missing:
            v["missing_count"] = len(miss)
            result.append(v)
    result.sort(key=lambda x: (x["missing_count"], x["recipe_id"], x["variant_id"]))
    return result