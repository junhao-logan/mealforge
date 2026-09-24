# app/shopping/services.py
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredients.models import Ingredient
from app.inventory.models import InventoryItem
from app.inventory.schemas import InventoryItemCreate
from app.inventory.services import create_inventory_item
from app.meal_plans.models import MealPlan, MealPlanEntry
from app.meal_plans.services import line_demand  # I13 需求公式(单一真相源)
from app.recipes.models import RecipeIngredient
from app.shopping.models import ShoppingList, ShoppingListItem

_CENT = Decimal("0.01")   # 需求量化精度, 对齐 needed_grams 的 Numeric(10,2)


async def _demand_and_stock(
    db: AsyncSession, user_id, start: date, end: date, *, today: date | None = None,
) -> tuple[dict[int, Decimal], dict[int, Decimal]]:
    """窗口内未完成餐的食材需求 + 当前库存, 各按食材聚合(克)。

    compute_shortfall(采购缺口) 与 compute_preview(库存预扣视图 I6) 的共享计算核。
    · 只算 is_completed=false 的 entry(已完成餐已扣库存, 再算需求会双重计数 D2)
    · scheduled_date ∈ [start, end](过期漏做餐排除)
    · 纯只读聚合, 无 N+1: JOIN 过滤用户 / IN 批量拉配料 / SUM 聚合库存
    返回 (demand, stock), 均为 {ingredient_id: grams}。
    """
    # ── 窗口内未完成 entry(entry 无 user_id, JOIN meal_plans 过滤归属) ──
    entries_stmt = (
        select(MealPlanEntry)
        .join(MealPlan, MealPlanEntry.meal_plan_id == MealPlan.id)
        .where(
            MealPlan.user_id == user_id,
            MealPlanEntry.is_completed.is_(False),
            MealPlanEntry.scheduled_date >= start,
            MealPlanEntry.scheduled_date <= end,
        )
    )
    entries = list((await db.execute(entries_stmt)).scalars().all())

    demand: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    if entries:
        # 涉及的所有配料(一条 IN 批量拉), 建 variant → [配料] 映射
        variant_ids = {e.recipe_variant_id for e in entries}
        ri_stmt = select(RecipeIngredient).where(
            RecipeIngredient.recipe_variant_id.in_(variant_ids)
        )
        ri_by_variant: dict[int, list[RecipeIngredient]] = defaultdict(list)
        for ri in (await db.execute(ri_stmt)).scalars().all():
            ri_by_variant[ri.recipe_variant_id].append(ri)
        # 聚合需求: 同一 variant 可被多餐用, 各乘各的份数
        for entry in entries:
            for ri in ri_by_variant.get(entry.recipe_variant_id, ()):
                demand[ri.ingredient_id] += line_demand(ri, entry)

    # ── 当前可用库存按食材聚合(净值, 不需批次/FEFO) ──
    # A4.1: 已过期批次不算「有」—— 与库存预留(I14)口径一致: 自动分配不用过期批次,
    # 所以库存页提示缺的, 采购这边也会让买
    today = today or date.today()
    stock_stmt = (
        select(InventoryItem.ingredient_id, func.sum(InventoryItem.quantity_grams))
        .where(
            InventoryItem.user_id == user_id,
            or_(InventoryItem.expires_at.is_(None), InventoryItem.expires_at >= today),
        )
        .group_by(InventoryItem.ingredient_id)
    )
    stock: dict[int, Decimal] = {
        ing_id: total for ing_id, total in (await db.execute(stock_stmt)).all()
    }
    return demand, stock


async def compute_shortfall(
    db: AsyncSession, user_id, start: date, end: date, *, today: date | None = None,
) -> list[dict]:
    """采购缺口(I7) = 窗口内未完成餐需求 − 当前库存, 仅留净缺口 > 0。

    返回 [{"ingredient_id", "shortfall_grams"}], 按 ingredient_id 升序。
    """
    demand, stock = await _demand_and_stock(db, user_id, start, end, today=today)

    shortfalls: list[dict] = []
    for ingredient_id, needed in demand.items():
        # 量化到 0.01g 再比: 需求最多 4 位小数(8,2 × 5,2), 库存 2 位,
        # 不量化会冒出 0.005g 这类无意义微缺口
        gap = needed.quantize(_CENT) - stock.get(ingredient_id, Decimal("0"))
        if gap > 0:
            shortfalls.append(
                {"ingredient_id": ingredient_id, "shortfall_grams": gap}
            )

    shortfalls.sort(key=lambda s: s["ingredient_id"])
    return shortfalls


async def in_flight_by_ingredient(db: AsyncSession, user_id) -> dict[int, Decimal]:
    """在途量(A8): 所有进行中清单里**还没买**、买了要入库的食材量, 按食材合计。

    这些量已经「安排要买」了, 缺口要先扣掉它们才是「还需要加」的 ——
    否则多张清单 / 缺口页反复加入 / 重算叠加手动项, 都会让同一样东西买两遍。
    """
    rows = (await db.execute(
        select(ShoppingListItem.ingredient_id, func.sum(ShoppingListItem.needed_grams))
        .join(ShoppingList, ShoppingListItem.shopping_list_id == ShoppingList.id)
        .where(
            ShoppingList.user_id == user_id,
            ShoppingList.status == "active",
            ShoppingListItem.is_purchased.is_(False),
            ShoppingListItem.add_to_inventory.is_(True),
            ShoppingListItem.ingredient_id.is_not(None),
            ShoppingListItem.needed_grams.is_not(None),
        )
        .group_by(ShoppingListItem.ingredient_id)
    )).all()
    return {ing_id: total for ing_id, total in rows}


async def ingredient_briefs(db: AsyncSession, ids) -> dict[int, dict]:
    """食材名 + 规范单位(前端不必再分页拉 /ingredients, 也不会把「块」写成 g)。"""
    ids = {i for i in ids if i is not None}
    if not ids:
        return {}
    return {
        ing.id: {"name": ing.name, "unit": ing.nutrition_basis_unit or "g"}
        for ing in (await db.execute(
            select(Ingredient).where(Ingredient.id.in_(ids))
        )).scalars().all()
    }


async def compute_preview(
    db: AsyncSession, user_id, start: date, end: date, *, today: date | None = None,
) -> list[dict]:
    """库存预扣视图(I6): 每个有库存或有需求的食材, 实际 / 需求 / 预计剩余。

    预计剩余 = 实际库存 − 窗口需求, **可负**(负 = 排的饭会缺这么多 → 驱动采购)。
    绝不真扣库存: 纯读时计算的视图, 不落库。
    返回 [{"ingredient_id", "actual_grams", "demand_grams",
          "projected_remaining_grams"}], 按 ingredient_id 升序。
    """
    demand, stock = await _demand_and_stock(db, user_id, start, end, today=today)

    in_flight = await in_flight_by_ingredient(db, user_id)
    ids = set(demand) | set(stock)
    briefs = await ingredient_briefs(db, ids)

    rows: list[dict] = []
    for ingredient_id in ids:
        actual = stock.get(ingredient_id, Decimal("0"))
        need = demand.get(ingredient_id, Decimal("0")).quantize(_CENT)
        remaining = actual - need
        in_list = in_flight.get(ingredient_id, Decimal("0"))
        info = briefs.get(ingredient_id, {})
        rows.append({
            "ingredient_id": ingredient_id,
            "name": info.get("name"),
            "unit": info.get("unit", "g"),
            "actual_grams": actual,
            "demand_grams": need,
            "projected_remaining_grams": remaining,   # 可负 = 会缺
            # A8: 已经在清单里等着买的量, 以及扣掉它之后还需要加的量
            "in_list_grams": in_list,
            "to_add_grams": max(Decimal("0"), -remaining - in_list),
        })

    rows.sort(key=lambda r: r["ingredient_id"])
    return rows


async def _materialize_auto_items(
    db: AsyncSession, sl: ShoppingList, *, today: date | None = None,
) -> None:
    """跑清单预测窗口的缺口, 把结果插成 source='auto' 条目。
    生成与重算共用。纯手动清单(无预测窗口)不产生 auto。调用方负责事务。
    """
    if sl.forecast_start is None or sl.forecast_end is None:
        return
    shortfalls = await compute_shortfall(
        db, sl.user_id, sl.forecast_start, sl.forecast_end, today=today
    )
    # A8: 先扣在途量(所有进行中清单里未购的, 含本清单的 manual; 本清单未购 auto 已在重算时删掉)
    in_flight = await in_flight_by_ingredient(db, sl.user_id)
    for s in shortfalls:
        need = s["shortfall_grams"] - in_flight.get(s["ingredient_id"], Decimal("0"))
        if need <= 0:
            continue                 # 已经安排要买够了, 不再重复加
        db.add(ShoppingListItem(
            shopping_list_id=sl.id,
            ingredient_id=s["ingredient_id"],
            source="auto",
            needed_grams=need,
            add_to_inventory=True,   # 食材项默认入库(→ I9 回流)
        ))
    await db.flush()


async def generate_shopping_list(
    db: AsyncSession,
    user_id,
    start: date,
    end: date,
    source_meal_plan_id: int | None = None,
    name: str | None = None,
    *,
    today: date | None = None,
) -> ShoppingList:
    """新建采购清单, 并按 [start, end] 缺口物化 auto 条目(方案 B: 生成即快照)。

    即使当前无缺口也会建出空清单(用户仍可手动加项)。调用方负责 commit。
    """
    sl = ShoppingList(
        user_id=user_id,
        name=name,
        source_meal_plan_id=source_meal_plan_id,
        forecast_start=start,
        forecast_end=end,
        status="active",
    )
    db.add(sl)
    await db.flush()   # 拿 sl.id 供子条目 FK
    await _materialize_auto_items(db, sl, today=today)
    return sl


async def regenerate_auto_items(
    db: AsyncSession, sl: ShoppingList, *, today: date | None = None,
) -> ShoppingList:
    """重算已有清单的 auto 条目:删未购 auto + 按新缺口重插。

    保留:已购 auto(冻结的历史事实)、全部 manual(用户所加)。
    已购项对应的食材若已回流入库, compute_shortfall 自然不再计入 —— 无需特判。
    调用方负责 commit。
    """
    await db.execute(
        delete(ShoppingListItem).where(
            ShoppingListItem.shopping_list_id == sl.id,
            ShoppingListItem.source == "auto",
            ShoppingListItem.is_purchased.is_(False),
        )
    )
    await _materialize_auto_items(db, sl, today=today)
    return sl


async def add_manual_item(
    db: AsyncSession, sl: ShoppingList, data
) -> ShoppingListItem:
    """往清单加一条 manual 条目(食材项或纯文本项)。调用方 commit。

    A8: 同一清单已有这个食材的**未购 manual 入库项**时, 把量并进那一行, 不新建。
    (auto 项不并 —— 重算会删掉未购 auto, 并进去的量会丢; 显示层会把 auto + manual 合成一行)
    """
    if data.ingredient_id is not None and data.add_to_inventory and data.needed_grams:
        existing = (await db.execute(
            select(ShoppingListItem).where(
                ShoppingListItem.shopping_list_id == sl.id,
                ShoppingListItem.ingredient_id == data.ingredient_id,
                ShoppingListItem.source == "manual",
                ShoppingListItem.is_purchased.is_(False),
                ShoppingListItem.add_to_inventory.is_(True),
            ).order_by(ShoppingListItem.id).limit(1)
        )).scalar_one_or_none()
        if existing is not None:
            existing.needed_grams = (existing.needed_grams or Decimal("0")) + data.needed_grams
            await db.flush()
            return existing

    item = ShoppingListItem(
        shopping_list_id=sl.id,
        ingredient_id=data.ingredient_id,
        item_name=data.item_name,
        source="manual",
        needed_grams=data.needed_grams,
        add_to_inventory=data.add_to_inventory,
        category_override=data.category_override,
        notes=data.notes,
    )
    db.add(item)
    await db.flush()
    return item


async def close_sibling_items(db: AsyncSession, item: ShoppingListItem) -> int:
    """A8: 同一清单里同一食材的其他未购入库项(显示时已合成一行)一起标记已购。

    实际购买量与入库批次只记在被结算的那一行上, 兄弟行不重复入库。返回关掉的行数。
    """
    if item.ingredient_id is None or not item.add_to_inventory:
        return 0
    siblings = (await db.execute(
        select(ShoppingListItem).where(
            ShoppingListItem.shopping_list_id == item.shopping_list_id,
            ShoppingListItem.ingredient_id == item.ingredient_id,
            ShoppingListItem.id != item.id,
            ShoppingListItem.is_purchased.is_(False),
            ShoppingListItem.add_to_inventory.is_(True),
        )
    )).scalars().all()
    for sib in siblings:
        sib.is_purchased = True
        sib.purchased_at = item.purchased_at
    await db.flush()
    return len(siblings)


async def mark_item_purchased(
    db: AsyncSession,
    item: ShoppingListItem,
    user_id,
    purchased_amount: Decimal | None = None,
    purchased_unit: str = "g",
    location: str | None = None,
    expires_at: date | None = None,
    *,
    today: date | None = None,
) -> ShoppingListItem:
    """打勾购买: 标记已购 + (若入库项)回流建库存批次(I9)。

    回流复用 inventory.create_inventory_item(建批次 + purchase 流水), 同事务原子完成;
    调用方负责 commit。Week 5/6 输入即克, purchased_grams = purchased_amount。
    """
    item.is_purchased = True
    item.purchased_at = datetime.now(UTC)
    if purchased_amount is not None:
        item.purchased_amount = purchased_amount
        item.purchased_unit = purchased_unit
        item.purchased_grams = purchased_amount   # 输入即克(Week 5/6)

    # 回流入库: 仅"入库项 + 关联食材 + 填了购买量"三者齐备时
    if (
        item.add_to_inventory
        and item.ingredient_id is not None
        and purchased_amount is not None
    ):
        await create_inventory_item(
            db, user_id,
            InventoryItemCreate(
                ingredient_id=item.ingredient_id,
                input_amount=purchased_amount,
                input_unit=purchased_unit,
                purchased_at=today or date.today(),
                location=location,
                expires_at=expires_at,
            ),
        )
    await db.flush()
    return item