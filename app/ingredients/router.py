from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.ingredients.models import Ingredient
from app.ingredients.schemas import IngredientCreate, IngredientRead
from app.users.models import User

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


def _normalize(name: str) -> str:
    # lower + 折叠空格; 与搜索、入库保持一致
    return " ".join(name.lower().split())


@router.get("", response_model=list[IngredientRead])
async def list_ingredients(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    # 分页: offset/limit 风格。limit 设上限 100 防止一次拉爆
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    # name 过滤: 可选,前缀匹配
    name: str | None = Query(None, min_length=1),
) -> list[Ingredient]:
    # 可见性过滤(I11): 只见 global 的 + 自己建的私有
    stmt = select(Ingredient).where(
        or_(
            Ingredient.visibility == "global",
            Ingredient.created_by_user_id == user.id,
        )
    )

    if name:
        # 查询词也 normalize,跟入库一致; LIKE 'xxx%' 前缀匹配走 name_normalized 索引
        stmt = stmt.where(Ingredient.name_normalized.like(f"{_normalize(name)}%"))

    # 稳定排序: 按 id,保证分页翻页顺序固定
    stmt = stmt.order_by(Ingredient.id).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=IngredientRead, status_code=201)
async def create_ingredient(
    payload: IngredientCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Ingredient:
    """创建私有食材(I11): source/visibility/归属由服务端固定, 客户端不可指定。"""
    ing = Ingredient(
        name=payload.name,
        name_normalized=_normalize(payload.name),
        category=payload.category,
        per_100g_calories=payload.per_100g_calories,
        per_100g_protein=payload.per_100g_protein,
        per_100g_carbs=payload.per_100g_carbs,
        per_100g_fat=payload.per_100g_fat,
        default_unit=payload.default_unit,
        grams_per_unit=payload.grams_per_unit,
        shelf_life_days=payload.shelf_life_days,
        source="user",
        visibility="private",
        created_by_user_id=user.id,
    )
    db.add(ing)
    await db.commit()
    await db.refresh(ing)
    return ing