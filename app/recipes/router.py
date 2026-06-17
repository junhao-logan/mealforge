from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.ingredients.models import Ingredient
from app.recipes.models import Recipe, RecipeVariant, RecipeIngredient
from app.recipes.schemas import (
    RecipeCreate, RecipeRead, RecipeListItem,
)
from app.recipes.services import resolve_grams, compute_variant_nutrition

router = APIRouter(prefix="/recipes", tags=["recipes"])


async def _load_full_recipe(db: AsyncSession, recipe_id: int) -> Recipe | None:
    """读完整菜谱: 预加载 variants → ingredients → ingredient, 避免 N+1。"""
    stmt = (
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.variants)
            .selectinload(RecipeVariant.ingredients)
            .selectinload(RecipeIngredient.ingredient)   
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


@router.post("", response_model=RecipeRead, status_code=201)
async def create_recipe(
    payload: RecipeCreate,
    db: AsyncSession = Depends(get_db),
) -> Recipe:
    # 1. 建 Recipe(source 固定 'user'; MVP 无认证, created_by 暂空)
    recipe = Recipe(
        name=payload.name,
        description=payload.description,
        cuisine=payload.cuisine,
        source="user",
        is_public=False,
    )

    # 2. 建第一个 Variant
    v = payload.variant
    variant = RecipeVariant(
        name=v.name, purpose_tag=v.purpose_tag, extra_notes=v.extra_notes,
        instructions=v.instructions, cooking_time_minutes=v.cooking_time_minutes,
        difficulty=v.difficulty, servings=v.servings,
    )

    # 3. 逐条配料: 查食材 → D5 换算克 → 建 RecipeIngredient
    #    先把要用的食材一次性查出来(避免循环里逐条查 = N+1)
    ing_ids = [ri.ingredient_id for ri in v.ingredients]
    ings = (await db.execute(
        select(Ingredient).where(Ingredient.id.in_(ing_ids))
    )).scalars().all()
    ing_map = {i.id: i for i in ings}

    for ri in v.ingredients:
        ingredient = ing_map.get(ri.ingredient_id)
        if ingredient is None:
            raise HTTPException(404, f"食材 id={ri.ingredient_id} 不存在")
        grams = await resolve_grams(db, ingredient, ri.input_amount, ri.input_unit)
        recipe_ing = RecipeIngredient(
            ingredient_id=ingredient.id,
            quantity_grams=grams,
            input_amount=ri.input_amount,
            input_unit=ri.input_unit,
        )
        recipe_ing.ingredient = ingredient  # 关联对象, 供聚合读 per-100g
        variant.ingredients.append(recipe_ing)

    # 4. D6 聚合营养, 写回 variant 缓存列
    compute_variant_nutrition(variant)

    # 5. 串起来, 一个事务提交(全成功或全回滚)
    variant.recipe = recipe
    db.add(recipe)
    await db.commit()

    # 6. 重新加载完整对象返回(含 DB 生成的 id / 时间戳)
    loaded = await _load_full_recipe(db, recipe.id)
    return loaded


@router.get("", response_model=list[RecipeListItem])
async def list_recipes(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[Recipe]:
    stmt = select(Recipe).order_by(Recipe.id).offset(skip).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{recipe_id}", response_model=RecipeRead)
async def get_recipe(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
) -> Recipe:
    recipe = await _load_full_recipe(db, recipe_id)
    if recipe is None:
        raise HTTPException(404, f"菜谱 id={recipe_id} 不存在")
    return recipe