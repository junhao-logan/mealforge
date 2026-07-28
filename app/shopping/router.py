# app/shopping/router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.meal_plans.models import MealPlan
from app.shopping.models import ShoppingList, ShoppingListItem
from app.shopping.schemas import (
    ShoppingItemCreate,
    ShoppingItemPurchase,
    ShoppingListGenerate,
    ShoppingListItemRead,
    ShoppingListListItem,
    ShoppingListRead,
)
from app.shopping.services import (
    add_manual_item,
    generate_shopping_list,
    mark_item_purchased,
    regenerate_auto_items,
)
from app.users.models import User

router = APIRouter(prefix="/shopping-lists", tags=["shopping"])


async def _get_owned_list(
    db: AsyncSession, list_id: int, user: User, *, with_items: bool = False
) -> ShoppingList:
    """取清单并校验归属: 不存在或非本人 → 404(不泄漏存在性)。"""
    stmt = select(ShoppingList).where(ShoppingList.id == list_id)
    if with_items:
        stmt = stmt.options(selectinload(ShoppingList.items))
    sl = (await db.execute(stmt)).scalar_one_or_none()
    if sl is None or sl.user_id != user.id:
        raise HTTPException(404, f"采购清单 id={list_id} 不存在")
    return sl


@router.post("", response_model=ShoppingListRead, status_code=201)
async def create_shopping_list(
    payload: ShoppingListGenerate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShoppingList:
    """生成清单: 物化缺口为 auto 条目(快照)。窗口来自计划或显式日期。"""
    start, end = payload.start_date, payload.end_date
    if payload.source_meal_plan_id is not None:
        # 校验计划归属, 并在未显式给日期时从计划推导窗口
        plan = (await db.execute(
            select(MealPlan).where(MealPlan.id == payload.source_meal_plan_id)
        )).scalar_one_or_none()
        if plan is None or plan.user_id != user.id:
            raise HTTPException(404, f"计划 id={payload.source_meal_plan_id} 不存在")
        start = start or plan.start_date
        end = end or plan.end_date

    sl = await generate_shopping_list(
        db, user.id, start, end,
        source_meal_plan_id=payload.source_meal_plan_id, name=payload.name,
    )
    await db.commit()
    # 重取(含条目): service 用 FK 插子行, sl.items 内存里未填充
    return await _get_owned_list(db, sl.id, user, with_items=True)


@router.get("", response_model=list[ShoppingListListItem])
async def list_shopping_lists(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ShoppingList]:
    stmt = (
        select(ShoppingList)
        .where(ShoppingList.user_id == user.id)
        .order_by(ShoppingList.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{list_id}", response_model=ShoppingListRead)
async def get_shopping_list(
    list_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShoppingList:
    return await _get_owned_list(db, list_id, user, with_items=True)


@router.post("/{list_id}/regenerate", response_model=ShoppingListRead)
async def regenerate_shopping_list(
    list_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShoppingList:
    """重算 auto 条目: 删未购 auto + 按新缺口重插; 保留已购与 manual。"""
    sl = await _get_owned_list(db, list_id, user)
    await regenerate_auto_items(db, sl)
    await db.commit()
    return await _get_owned_list(db, sl.id, user, with_items=True)


@router.delete("/{list_id}", status_code=204)
async def delete_shopping_list(
    list_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    sl = await _get_owned_list(db, list_id, user)
    await db.delete(sl)   # 条目走 CASCADE
    await db.commit()


async def _get_owned_item(
    db: AsyncSession, list_id: int, item_id: int, user: User
) -> ShoppingListItem:
    """取条目并校验归属(经清单关联 user)。"""
    sl = await _get_owned_list(db, list_id, user)
    item = await db.get(ShoppingListItem, item_id)
    if item is None or item.shopping_list_id != sl.id:
        raise HTTPException(404, f"采购项 id={item_id} 不存在")
    return item


@router.post("/{list_id}/items", response_model=ShoppingListItemRead, status_code=201)
async def add_item(
    list_id: int,
    payload: ShoppingItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShoppingListItem:
    """手动加一条采购项(食材项或纯文本项)。"""
    sl = await _get_owned_list(db, list_id, user)
    item = await add_manual_item(db, sl, payload)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch(
    "/{list_id}/items/{item_id}/purchase", response_model=ShoppingListItemRead
)
async def purchase_item(
    list_id: int,
    item_id: int,
    payload: ShoppingItemPurchase,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShoppingListItem:
    """打勾购买 → 入库项回流建批次(I9)。"""
    item = await _get_owned_item(db, list_id, item_id, user)
    if item.is_purchased:
        raise HTTPException(400, "该采购项已购买")
    # 入库项必须填实际购买量, 否则无法建批次
    if item.add_to_inventory and payload.purchased_amount is None:
        raise HTTPException(422, "入库项需填 purchased_amount(实际购买量)")

    await mark_item_purchased(
        db, item, user.id,
        purchased_amount=payload.purchased_amount,
        purchased_unit=payload.purchased_unit,
    )
    await db.commit()
    await db.refresh(item)
    return item