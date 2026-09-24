from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.schemas import RecipeGenerateRequest
from app.ai.services import (
    AiError,
    EmptyInventoryError,
    RecipeValidationError,
    generate_recipe,
)
from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.ingredients.access import ensure_visible_ingredients
from app.recipes.models import Recipe, RecipeIngredient, RecipeVariant
from app.recipes.schemas import (
    RecipeCreate,
    RecipeListItem,
    RecipeRead,
    RecipeRecommendation,
)
from app.recipes.services import (
    compute_variant_nutrition,
    recipe_visible_to,
    recommend_recipes,
    resolve_quantity,
)
from app.users.models import User

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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Recipe:
    # 1. 建 Recipe(私有创建 I11: source='user', visibility='private', 归属=当前用户)
    recipe = Recipe(
        name=payload.name,
        description=payload.description,
        cuisine=payload.cuisine,
        source="user",
        visibility="private",
        created_by_user_id=user.id,
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
    #    只能引用自己看得见的食材(I11): 别人的私有食材一律 404
    ing_map = await ensure_visible_ingredients(
        db, user.id, [ri.ingredient_id for ri in v.ingredients]
    )

    for ri in v.ingredients:
        ingredient = ing_map[ri.ingredient_id]
        quantity = resolve_quantity(ingredient, ri.input_amount, ri.input_unit)
        recipe_ing = RecipeIngredient(
            ingredient_id=ingredient.id,
            quantity_grams=quantity,
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


@router.post("/generate", response_model=RecipeRead, status_code=201)
async def generate_recipe_endpoint(
    payload: RecipeGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Recipe:
    """AI 从库存生成菜谱(Week 7)。空库存 400;AI 侧失败 502。"""
    try:
        return await generate_recipe(
            db, user,
            free_text=payload.free_text, cuisine=payload.cuisine,
            goal=payload.goal, servings=payload.servings,
        )
    except EmptyInventoryError as e:
        raise HTTPException(400, str(e)) from e
    except (AiError, RecipeValidationError) as e:
        # 上游 AI 失败或返回无效结果 —— 已记 failed 日志; 对客户端报 502
        raise HTTPException(502, "AI 生成暂时不可用, 请稍后重试") from e


@router.get("", response_model=list[RecipeListItem])
async def list_recipes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict]:
    # 同时带出每道菜的第一个做法 id(最早建的那个), 一条查询, 不必逐个取详情
    first_variant = (
        select(RecipeVariant.recipe_id, func.min(RecipeVariant.id).label("vid"))
        .group_by(RecipeVariant.recipe_id)
        .subquery()
    )
    stmt = (
        select(Recipe, first_variant.c.vid)
        .outerjoin(first_variant, first_variant.c.recipe_id == Recipe.id)
        .where(recipe_visible_to(user.id))
        .order_by(Recipe.id).offset(skip).limit(limit)
    )
    return [
        {**RecipeListItem.model_validate(r).model_dump(), "default_variant_id": vid}
        for r, vid in (await db.execute(stmt)).all()
    ]


@router.get("/recommendations", response_model=list[RecipeRecommendation])
async def recipe_recommendations(
    max_missing: int = Query(2, ge=0, le=10),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """反向推荐(功能B): 库存能做哪些已有菜谱做法, 缺 ≤max_missing 样也列出。

    ⚠️ 必须注册在 GET /{recipe_id} 之前, 否则 "recommendations" 被当 recipe_id。
    """
    return await recommend_recipes(db, user, max_missing=max_missing)


@router.get("/{recipe_id}", response_model=RecipeRead)
async def get_recipe(
    recipe_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Recipe:
    recipe = await _load_full_recipe(db, recipe_id)
    # 不存在, 或既非 global 又非本人所建 → 一律 404(不泄漏存在性)
    if recipe is None or (
        recipe.visibility != "global" and recipe.created_by_user_id != user.id
    ):
        raise HTTPException(404, f"菜谱 id={recipe_id} 不存在")
    return recipe