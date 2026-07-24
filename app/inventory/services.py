# app/inventory/services.py
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.inventory.models import InventoryItem, InventoryTransaction
from app.inventory.schemas import InventoryItemCreate, InventoryItemUpdate
from datetime import date, timedelta
from decimal import Decimal
from app.recipes.models import RecipeIngredient
from app.meal_plans.models import MealPlanEntry

from app.core.config import get_settings

async def create_inventory_item(
    db: AsyncSession, user_id, data: InventoryItemCreate
) -> InventoryItem:
    """入库一个批次 + 记一条 purchase 流水(I2)。
    两张表同事务写入: flush 拿 item.id, 由 router 统一 commit。
    Week 5: 输入即克, quantity_grams = input_amount。
    """
    # 1) 建库存批次(model 对象)。quantity_grams = 输入量(克本位, I3)
    item = InventoryItem(
        user_id=user_id,
        ingredient_id=data.ingredient_id,
        quantity_grams=data.input_amount,   # 输入即克
        input_amount=data.input_amount,     # D5=B: 原始输入也存, 展示用
        input_unit=data.input_unit,
        purchased_at=data.purchased_at,
        expires_at=data.expires_at,
        location=data.location,
    )
    db.add(item)
    await db.flush()   # flush 让 DB 生成 item.id, 但不提交(供下面流水引用)

    # 2) 记一条入库流水(+ delta, reason=purchase)。审计用(I2)
    txn = InventoryTransaction(
        user_id=user_id,
        ingredient_id=data.ingredient_id,
        inventory_item_id=item.id,          # 关联刚建的批次
        delta_grams=data.input_amount,      # 入库为正
        reason="purchase",
    )
    db.add(txn)
    await db.flush()

    return item

def compute_expiry_status(expires_at: date | None, today: date, warning_days: int) -> str | None:
    """I4: 临期状态 = f(expires_at, 今天)。查询时算,不落库。
    None 表示不临期或无过期日(NULL 显式排除, 永不提醒)。
    """
    if expires_at is None:
        return None
    days_left = (expires_at - today).days
    return "expiring" if days_left <= warning_days else None


async def list_inventory_items(db: AsyncSession, user_id) -> list[InventoryItem]:
    """列出用户库存, FEFO 序(先过期先扣的顺序 = 展示顺序)。
    expires_at NULL 排最后; 同过期日按 purchased_at 先买先前(I1)。
    """
    stmt = (
        select(InventoryItem)
        .where(InventoryItem.user_id == user_id)
        .order_by(
            InventoryItem.expires_at.asc().nulls_last(),
            InventoryItem.purchased_at.asc().nulls_last(),
            InventoryItem.id.asc(),      
        )
    )
    return list((await db.execute(stmt)).scalars().all())

async def deduct_for_entry(
    db: AsyncSession, user_id, entry: MealPlanEntry
) -> list[dict]:
    """完成餐次 → 按 FEFO 扣减库存(I1)。
    · 需求 = RecipeIngredient.quantity_grams × entry.servings (I13: 配方倍数)
    · 按 expires_at ASC NULLS LAST, purchased_at ASC 逐批扣(FEFO)
    · 扣到 0 不下穿; 不足部分作为短缺返回, 不写回库存(I1)
    · 每笔扣减记 meal_consumption 流水, 关联 source_entry_id (I2)
    不 commit —— 由 router 与 entry.is_completed 同事务提交。
    返回: [{"ingredient_id": int, "shortfall_grams": Decimal}, ...]
    """
    # 1) 取这道菜的配料
    ri_stmt = select(RecipeIngredient).where(
        RecipeIngredient.recipe_variant_id == entry.recipe_variant_id
    )
    recipe_ingredients = list((await db.execute(ri_stmt)).scalars().all())

    shortfalls: list[dict] = []

    for ri in recipe_ingredients:
        needed = ri.quantity_grams * entry.servings   # I13: 直接乘, 不除

        # 2) 取该食材的可用批次, FEFO 序(与 list 展示同序)
        batch_stmt = (
            select(InventoryItem)
            .where(
                InventoryItem.user_id == user_id,
                InventoryItem.ingredient_id == ri.ingredient_id,
                InventoryItem.quantity_grams > 0,      # 跳过扣光的零批次
            )
            .order_by(
                InventoryItem.expires_at.asc().nulls_last(),
                InventoryItem.purchased_at.asc().nulls_last(),
                InventoryItem.id.asc(), 
            )
            .with_for_update()   # 行锁: 防并发完成餐次时重复扣同一批次
        )
        batches = list((await db.execute(batch_stmt)).scalars().all())

        # 3) 逐批扣, 扣光就下一批
        remaining = needed
        for b in batches:
            if remaining <= 0:
                break
            take = min(b.quantity_grams, remaining)   # 这批最多能给多少
            b.quantity_grams -= take                  # 扣(ORM 追踪, flush 时 UPDATE)
            remaining -= take

            db.add(InventoryTransaction(
                user_id=user_id,
                ingredient_id=ri.ingredient_id,
                inventory_item_id=b.id,
                delta_grams=-take,                    # 扣减为负
                reason="meal_consumption",
                source_entry_id=entry.id,             # 谁导致的
            ))

        # 4) 批次扣完还不够 → 记短缺(不写回库存, I1)
        if remaining > 0:
            shortfalls.append({
                "ingredient_id": ri.ingredient_id,
                "shortfall_grams": remaining,
            })

    await db.flush()
    return shortfalls

async def get_owned_item(db: AsyncSession, user_id, item_id: int) -> InventoryItem | None:
    """取批次并校验归属。不是自己的 → None(router 转 404, 不泄漏存在性)。"""
    item = await db.get(InventoryItem, item_id)
    if item is None or item.user_id != user_id:
        return None
    return item


async def update_inventory_item(
    db: AsyncSession, item: InventoryItem, data: InventoryItemUpdate
) -> InventoryItem:
    """盘点修正: 只改当前余量与日期。input_amount/unit 是入库时的原始记录, 不改。
    不记流水(I2 补充: 人工调整非消耗事件)。
    """
    if data.quantity_grams is not None:
        item.quantity_grams = data.quantity_grams   # 只改余量
    if data.purchased_at is not None:
        item.purchased_at = data.purchased_at
    if data.expires_at is not None:
        item.expires_at = data.expires_at
    if data.location is not None:
        item.location = data.location
    await db.flush()
    return item