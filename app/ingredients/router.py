from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.ingredients.models import Ingredient
from app.ingredients.schemas import IngredientRead

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.get("", response_model=list[IngredientRead])
async def list_ingredients(
    db: AsyncSession = Depends(get_db),
    # 分页: offset/limit 风格。limit 设上限 100 防止一次拉爆
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    # name 过滤: 可选,前缀匹配
    name: str | None = Query(None, min_length=1),
) -> list[Ingredient]:
    stmt = select(Ingredient)

    if name:
        # 查询词也 normalize(lower + 折叠空格),跟入库时一致,
        # 保证 "chicken" 能匹配到 "Chicken breast"。
        # LIKE 'xxx%' 前缀匹配,走 name_normalized 上的索引(ERD 已锁)。
        normalized = " ".join(name.lower().split())
        stmt = stmt.where(Ingredient.name_normalized.like(f"{normalized}%"))

    # 稳定排序: 按 id,保证分页翻页顺序固定(否则 PG 返回顺序不保证)
    stmt = stmt.order_by(Ingredient.id).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())