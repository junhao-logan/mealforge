# app/ingredients/access.py
"""食材的共享小工具: 名字规范化、可见性(I11)、按 id 批量取名字与单位。

之前这三件事在 ingredients / recipes / ai / inventory / shopping 各写一份,
其中几处创建端点**漏了可见性校验** —— 能引用别人的私有食材(名字随后出现在自己的库存 / 采购里)。
统一到这里, 所有「用户传 ingredient_id 进来」的写入口都走 `ensure_visible_ingredients`。
"""
from __future__ import annotations

from collections.abc import Iterable

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredients.models import Ingredient


def normalize_name(name: str) -> str:
    """lower + 去首尾空白 + 折叠连续空格。搜索、入库、种子、AI 去重共用。"""
    return " ".join(name.lower().split())


def visible_to(user_id):
    """可见性条件(I11): global 的 + 自己建的私有。"""
    return or_(Ingredient.visibility == "global", Ingredient.created_by_user_id == user_id)


async def ensure_visible_ingredients(
    db: AsyncSession, user_id, ids: Iterable[int]
) -> dict[int, Ingredient]:
    """按 id 批量取「当前用户看得见」的食材; 有任何一个不存在或不可见 → 404(不泄漏存在性)。"""
    wanted = {i for i in ids if i is not None}
    if not wanted:
        return {}
    found = {
        ing.id: ing for ing in (await db.execute(
            select(Ingredient).where(Ingredient.id.in_(wanted), visible_to(user_id))
        )).scalars().all()
    }
    missing = sorted(wanted - found.keys())
    if missing:
        raise HTTPException(404, f"食材 id={missing[0]} 不存在")
    return found


async def ingredient_briefs(db: AsyncSession, ids: Iterable[int]) -> dict[int, dict]:
    """食材名 + 规范单位(前端不必再分页拉 /ingredients, 也不会把「块」写成 g)。

    调用方传入的 id 都来自用户自己的数据(库存 / 清单 / 餐次), 可见性已在写入时保证。
    """
    wanted = {i for i in ids if i is not None}
    if not wanted:
        return {}
    return {
        ing.id: {"name": ing.name, "unit": ing.nutrition_basis_unit or "g"}
        for ing in (await db.execute(
            select(Ingredient).where(Ingredient.id.in_(wanted))
        )).scalars().all()
    }
