from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredients.models import Ingredient
from app.recipes.models import RecipeVariant


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
    from sqlalchemy import func as _func  # 局部 import 避免顶部杂乱
    # nutrition_computed_at 用 DB 时间, 这里用 Python now 也可; 简单起见标记已算
    from datetime import datetime, timezone
    variant.nutrition_computed_at = datetime.now(timezone.utc)