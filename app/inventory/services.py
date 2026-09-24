# app/inventory/services.py
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredients.access import ensure_visible_ingredients, ingredient_briefs
from app.inventory.models import EntryBatchPick, InventoryItem, InventoryTransaction
from app.inventory.reservations import (
    compute_reservations,
    fefo_key,
    hard_reserved,
    is_expired,
    quantize_amount,
)
from app.inventory.schemas import InventoryItemCreate, InventoryItemUpdate
from app.meal_plans.models import MealPlanEntry
from app.meal_plans.services import line_demand  # I13 需求公式(单一真相源)
from app.recipes.models import RecipeIngredient
from app.recipes.services import resolve_quantity


async def create_inventory_item(
    db: AsyncSession, user_id, data: InventoryItemCreate
) -> InventoryItem:
    """入库一个批次 + 记一条 purchase 流水(I2)。
    两张表同事务写入: flush 拿 item.id, 由 router 统一 commit。
    A2: 按食材规范单位换算 —— input_unit 经 resolve_quantity 转成规范单位下的量存入
    quantity_grams(质量食材=克; 单位本位食材=个/块)。
    """
    # 0) 取食材(只能用自己看得见的, I11), 用其规范单位换算输入量
    #    (单位本位食材只接受自己的单位, 不接受克)
    ingredient = (await ensure_visible_ingredients(db, user_id, [data.ingredient_id]))[
        data.ingredient_id
    ]
    quantity = resolve_quantity(ingredient, data.input_amount, data.input_unit)

    # 1) 建库存批次。quantity_grams = 换算后的规范单位量(I3 克本位 / A2 单位本位)
    item = InventoryItem(
        user_id=user_id,
        ingredient_id=data.ingredient_id,
        quantity_grams=quantity,            # 规范单位下的量
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
        delta_grams=quantity,               # 入库为正(规范单位)
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


async def list_inventory_items(
    db: AsyncSession, user_id, *, include_empty: bool = False,
) -> list[InventoryItem]:
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
    if not include_empty:
        # A6: 用到 0 的批次保留在库里(退回原批次要用, I1), 但默认不返回
        stmt = stmt.where(InventoryItem.quantity_grams > 0)
    return list((await db.execute(stmt)).scalars().all())

async def deduct_for_entry(
    db: AsyncSession, user_id, entry: MealPlanEntry, *, today: date | None = None,
) -> list[dict]:
    """完成餐次 → 扣减库存。规则与预留视图(reservations.py)完全一致, 显示什么就扣什么(A4):
    1. 先扣该餐的**手选批次**(按勾选顺序, 过期的也可以 —— 用户自己选的)
    2. 剩余需求按 FEFO 从**未过期**批次里扣; 过期批次自动分配绝不碰
    3. 其他未完成餐次手选的量是硬预留, 这里要让开(可用 = 批次余量 − 别人手选的)
    · 需求 = RecipeIngredient.quantity_grams × entry.servings (I13), 同食材多行合并
    · 扣到 0 不下穿; 不足部分作为短缺返回, 不写回库存(I1)
    · 每笔扣减记 meal_consumption 流水, 关联 source_entry_id (I2)
    不 commit —— 由 router 与 entry.is_completed 同事务提交。
    返回: [{"ingredient_id": int, "shortfall_grams": Decimal}, ...]
    """
    today = today or date.today()

    # 0) 其他餐次的手选硬预留(排除本餐)
    others = hard_reserved(
        await compute_reservations(db, user_id, today=today, exclude_entry_id=entry.id)
    )

    # 1) 这道菜的配料, 同食材合并需求(保持配方顺序)
    ri_stmt = select(RecipeIngredient).where(
        RecipeIngredient.recipe_variant_id == entry.recipe_variant_id
    ).order_by(RecipeIngredient.id)
    needs: dict[int, Decimal] = {}
    for ri in (await db.execute(ri_stmt)).scalars().all():
        needs[ri.ingredient_id] = needs.get(ri.ingredient_id, Decimal("0")) + line_demand(ri, entry)
    # 量化到 0.01, 与预留视图同口径; 否则 1.5 × 33.33 = 49.995 扣 49.99、流水记 -50.00,
    # 撤销时按流水退 50.00, 每轮「完成 → 撤销」凭空多出 0.01
    needs = {i: quantize_amount(n) for i, n in needs.items()}

    # 2) 本餐手选(按勾选顺序)
    picks: dict[int, list[int]] = {}
    for p in (await db.execute(
        select(EntryBatchPick)
        .where(EntryBatchPick.entry_id == entry.id)
        .order_by(EntryBatchPick.position)
    )).scalars().all():
        picks.setdefault(p.ingredient_id, []).append(p.inventory_item_id)

    shortfalls: list[dict] = []
    if not needs:
        await db.flush()
        return shortfalls

    # 3) 所有相关批次一次取出并加行锁(防并发完成餐次时重复扣同一批次)。
    #    一条查询代替「每种食材一条」(N+1); ORDER BY id 让加锁顺序固定, 两个请求不会互相等成死锁
    locked = (await db.execute(
        select(InventoryItem)
        .where(
            InventoryItem.user_id == user_id,
            InventoryItem.ingredient_id.in_(needs.keys()),
            InventoryItem.quantity_grams > 0,          # 跳过扣光的零批次
        )
        .order_by(InventoryItem.id)
        .with_for_update()
        # 上面 compute_reservations 已把这些批次无锁读进了 session; 不加这个, 拿到锁后
        # 返回的仍是 session 里的旧对象(旧余量), 两个请求同时扣同一批时会丢一次扣减
        .execution_options(populate_existing=True)
    )).scalars().all()
    by_ingredient: dict[int, list[InventoryItem]] = {}
    for b in locked:
        by_ingredient.setdefault(b.ingredient_id, []).append(b)

    for ingredient_id, needed in needs.items():
        batches = sorted(by_ingredient.get(ingredient_id, []), key=fefo_key)
        by_id = {b.id: b for b in batches}

        remaining = needed
        # 3a) 手选批次优先(按勾选顺序), 3b) 其余走 FEFO, 只用未过期批次
        order = [by_id[bid] for bid in picks.get(ingredient_id, ()) if bid in by_id]
        order += [b for b in batches if not is_expired(b.expires_at, today)]
        for b in order:
            if remaining <= 0:
                break
            avail = b.quantity_grams - others.get(b.id, Decimal("0"))   # 让开别人手选的
            take = min(avail, remaining)
            if take <= 0:
                continue
            b.quantity_grams -= take                  # 扣(ORM 追踪, flush 时 UPDATE)
            remaining -= take
            db.add(InventoryTransaction(
                user_id=user_id,
                ingredient_id=ingredient_id,
                inventory_item_id=b.id,
                delta_grams=-take,                    # 扣减为负
                reason="meal_consumption",
                source_entry_id=entry.id,             # 谁导致的
            ))

        # 4) 还不够 → 记短缺(不写回库存, I1)
        if remaining > 0:
            shortfalls.append({
                "ingredient_id": ingredient_id,
                "shortfall_grams": remaining,
            })

    await db.flush()
    return shortfalls


async def restock_for_entry(db: AsyncSession, user_id, entry: MealPlanEntry) -> list[dict]:
    """撤销完成 / 删除已完成餐次 → 把该 entry 完成时扣掉的库存原样退回原批次(I2)。

    幂等/健壮做法: **按 source_entry_id 净额回补**, 而非逐条反转。
    · 对该 entry 的所有流水按 (批次, 食材) 聚合 delta_grams:
      完成时扣减为负、之前撤销回补为正, 净额 = 当前仍欠该批次的量。
    · 净额为负(仍有未回补的消耗)才回补, 回补 = -净额(正); 已净平则跳过
      —— 这样 完成→撤销→再完成→再撤销 循环也不会重复回补。
    · 零余量批次被保留(I1 / A6), 所以扣光的批次也能退回原批次(保留原过期日 / 储存区)。
    · 原批次已被手动删除(inventory_item_id 置空)的**退不回去**:
      不建新批次(流水里没有过期日 / 储存区), 记一条 reason='reversal_lost' 的冲销流水
      让净额归零(下次不会重复报), 并把这部分返回给调用方提示用户(A5)。
    不 commit —— 由 router 同事务提交。
    返回: 退不回去的部分 [{"ingredient_id", "amount"}], 按食材合并。
    """
    rows = (await db.execute(
        select(
            InventoryTransaction.inventory_item_id,
            InventoryTransaction.ingredient_id,
            func.sum(InventoryTransaction.delta_grams),
        )
        .where(InventoryTransaction.source_entry_id == entry.id)
        .group_by(
            InventoryTransaction.inventory_item_id,
            InventoryTransaction.ingredient_id,
        )
    )).all()

    owed = [(i, ing, -(net or Decimal("0"))) for i, ing, net in rows]
    owed = [o for o in owed if o[2] > 0]        # 净消耗为负 → 回补为正; 已净平的跳过

    # 原批次一次取出并加行锁(代替逐批查询), 按 id 排序固定加锁顺序
    batch_ids = {i for i, _, _ in owed if i is not None}
    batches = {}
    if batch_ids:
        batches = {
            b.id: b for b in (await db.execute(
                select(InventoryItem)
                .where(InventoryItem.id.in_(batch_ids))
                .order_by(InventoryItem.id)
                .with_for_update()
                .execution_options(populate_existing=True)   # 拿锁后读最新余量
            )).scalars().all()
        }

    lost: dict[int, Decimal] = {}
    for item_id, ingredient_id, give_back in owed:
        batch = batches.get(item_id) if item_id is not None else None

        if batch is None:
            # 原批次已删: 退不回去 → 冲销流水(不动库存), 记入返回
            lost[ingredient_id] = lost.get(ingredient_id, Decimal("0")) + give_back
            db.add(InventoryTransaction(
                user_id=user_id,
                ingredient_id=ingredient_id,
                inventory_item_id=None,
                delta_grams=give_back,
                reason="reversal_lost",
                source_entry_id=entry.id,
            ))
            continue

        batch.quantity_grams += give_back
        db.add(InventoryTransaction(
            user_id=user_id,
            ingredient_id=ingredient_id,
            inventory_item_id=item_id,
            delta_grams=give_back,              # 回补为正
            reason="meal_reversal",            # 撤销完成的反向流水
            source_entry_id=entry.id,
        ))

    await db.flush()
    return [{"ingredient_id": i, "amount": a} for i, a in sorted(lost.items())]


async def describe_losses(db: AsyncSession, losses: list[dict]) -> list[dict]:
    """给「退不回去」的条目补上食材名和规范单位, 供前端提示。"""
    briefs = await ingredient_briefs(db, [x["ingredient_id"] for x in losses])
    return [
        {
            **x,
            "name": briefs.get(x["ingredient_id"], {}).get("name"),
            "unit": briefs.get(x["ingredient_id"], {}).get("unit", "g"),
        }
        for x in losses
    ]


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
    # 只处理请求里**显式传了**的字段(exclude_unset): 这样传 null 能清空过期日 / 储存区,
    # 没传的字段保持不变。之前用「is not None」判断, 前端清空过期日会被静默忽略。
    sent = data.model_dump(exclude_unset=True)
    if sent.get("quantity_grams") is not None:         # 余量不能清空, null 视为未改
        item.quantity_grams = sent["quantity_grams"]   # 只改余量
    for field in ("purchased_at", "expires_at", "location"):
        if field in sent:
            setattr(item, field, sent[field])
    await db.flush()
    return item