# app/inventory/reservations.py
"""库存预留视图(A4): 未完成餐次对各库存批次的预留 —— 读时模拟, 不落库(I6)。

两阶段分配, 与真实扣减(deduct_for_entry)共用同一套规则:
  1. 手选(硬预留): 用户为某餐某食材勾选的批次, 按勾选顺序取够。可以是过期批次。
  2. 自动(软预留): 剩余需求按餐次时间先后, 走 FEFO 从**未过期**批次里取。
     取不够的记为缺口 —— 自动分配绝不碰过期批次(A4 决策)。
餐次顺序 = 日期 → 早/午/晚 → sort_order → id。按这个顺序做饭时, 模拟结果与真实扣减一致。

只看今天及以后、未完成的餐次(已过日期没做的不占库存)。
查询: 餐次 / 配料 / 批次 / 手选 / 食材名 各 1 条, 无 N+1; 分配全在内存。
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredients.models import Ingredient
from app.inventory.models import EntryBatchPick, InventoryItem
from app.meal_plans.models import MealPlan, MealPlanEntry
from app.meal_plans.services import line_demand, meal_type_sort_key
from app.recipes.models import Recipe, RecipeIngredient, RecipeVariant

_ZERO = Decimal("0")
_CENT = Decimal("0.01")


def is_expired(expires_at: date | None, today: date) -> bool:
    """过期 = 过期日早于今天。当天到期的还能用; 无过期日永不过期。"""
    return expires_at is not None and expires_at < today


def fefo_key(item: InventoryItem):
    """FEFO 全序(I1): 过期日 → 购买日 → id, NULL 排最后。与扣减 SQL 的 ORDER BY 一致。"""
    return (
        item.expires_at is None, item.expires_at or date.max,
        item.purchased_at is None, item.purchased_at or date.max,
        item.id,
    )


@dataclass
class _Line:
    """一餐一食材的需求(同一食材在配方里出现多次时合并)。"""
    ingredient_id: int
    need: Decimal
    picked: list[int] = field(default_factory=list)      # 手选批次 id, 按勾选顺序
    allocations: list[dict] = field(default_factory=list)
    left: Decimal = _ZERO                                # 还没分到的量


def _q(v: Decimal) -> Decimal:
    return v.quantize(_CENT)


async def compute_reservations(
    db: AsyncSession, user_id, *, today: date | None = None,
    exclude_entry_id: int | None = None,
) -> dict:
    """算出每个批次被哪些餐次预留了多少, 每个餐次从哪些批次取, 以及缺口。

    exclude_entry_id: 把某个餐次整个排除在外 —— 用于
      · 手选校验(该餐自己的占用不算"已被预留")
      · 完成扣减时取「其他餐次的手选硬预留」
    """
    today = today or date.today()

    # ── 1. 今天及以后、未完成的餐次(带计划名 / 菜名) ──
    stmt = (
        select(MealPlanEntry, MealPlan.name, MealPlan.plan_type, Recipe.name)
        .join(MealPlan, MealPlanEntry.meal_plan_id == MealPlan.id)
        .join(RecipeVariant, MealPlanEntry.recipe_variant_id == RecipeVariant.id)
        .join(Recipe, RecipeVariant.recipe_id == Recipe.id)
        .where(
            MealPlan.user_id == user_id,
            MealPlanEntry.is_completed.is_(False),
            MealPlanEntry.scheduled_date >= today,
        )
    )
    if exclude_entry_id is not None:
        stmt = stmt.where(MealPlanEntry.id != exclude_entry_id)
    rows = (await db.execute(stmt)).all()
    rows.sort(key=lambda r: (
        r[0].scheduled_date, meal_type_sort_key(r[0].meal_type), r[0].sort_order, r[0].id,
    ))
    entries = [r[0] for r in rows]
    meta = {r[0].id: {"plan_name": r[1], "plan_type": r[2], "recipe_name": r[3]} for r in rows}

    # ── 2. 配料 → 每餐每食材的需求 ──
    lines: dict[int, dict[int, _Line]] = {e.id: {} for e in entries}
    if entries:
        ri_rows = (await db.execute(
            select(RecipeIngredient).where(
                RecipeIngredient.recipe_variant_id.in_({e.recipe_variant_id for e in entries})
            ).order_by(RecipeIngredient.id)
        )).scalars().all()
        ri_by_variant: dict[int, list[RecipeIngredient]] = defaultdict(list)
        for ri in ri_rows:
            ri_by_variant[ri.recipe_variant_id].append(ri)
        for e in entries:
            for ri in ri_by_variant.get(e.recipe_variant_id, ()):
                ln = lines[e.id].setdefault(ri.ingredient_id, _Line(ri.ingredient_id, _ZERO))
                ln.need += line_demand(ri, e)
        for per_entry in lines.values():
            for ln in per_entry.values():
                ln.need = _q(ln.need)
                ln.left = ln.need

    # ── 3. 当前有余量的批次(FEFO 序) ──
    batches = sorted((await db.execute(
        select(InventoryItem).where(
            InventoryItem.user_id == user_id, InventoryItem.quantity_grams > 0,
        )
    )).scalars().all(), key=fefo_key)
    remaining = {b.id: b.quantity_grams for b in batches}
    by_id = {b.id: b for b in batches}
    batch_allocs: dict[int, list[dict]] = defaultdict(list)
    order = {e.id: i for i, e in enumerate(entries)}

    # ── 4. 手选 ──
    if entries:
        picks = (await db.execute(
            select(EntryBatchPick)
            .where(EntryBatchPick.entry_id.in_(list(lines)))
            .order_by(EntryBatchPick.entry_id, EntryBatchPick.position)
        )).scalars().all()
        for p in picks:
            ln = lines[p.entry_id].get(p.ingredient_id)
            if ln is not None:
                ln.picked.append(p.inventory_item_id)

    def _take(entry_id: int, ln: _Line, b: InventoryItem, manual: bool) -> None:
        take = min(remaining[b.id], ln.left)
        if take <= 0:
            return
        remaining[b.id] -= take
        ln.left -= take
        ln.allocations.append({"batch_id": b.id, "amount": take, "manual": manual})
        batch_allocs[b.id].append({"entry_id": entry_id, "amount": take, "manual": manual})

    # 阶段 1: 手选(硬预留, 先于一切自动分配)
    for e in entries:
        for ln in lines[e.id].values():
            for bid in ln.picked:
                b = by_id.get(bid)
                if b is not None and b.ingredient_id == ln.ingredient_id:
                    _take(e.id, ln, b, manual=True)

    # 阶段 2: 自动(按餐次先后, FEFO, 跳过过期批次)
    fresh_by_ing: dict[int, list[InventoryItem]] = defaultdict(list)
    for b in batches:
        if not is_expired(b.expires_at, today):
            fresh_by_ing[b.ingredient_id].append(b)
    for e in entries:
        for ln in lines[e.id].values():
            for b in fresh_by_ing.get(ln.ingredient_id, ()):
                if ln.left <= 0:
                    break
                _take(e.id, ln, b, manual=False)

    # ── 5. 汇总输出 ──
    shortfall_by_ing: dict[int, Decimal] = defaultdict(lambda: _ZERO)
    entries_out = []
    for e in entries:
        lines_out = []
        for ln in lines[e.id].values():
            if ln.left > 0:
                shortfall_by_ing[ln.ingredient_id] += ln.left
            lines_out.append({
                "ingredient_id": ln.ingredient_id,
                "need": ln.need,
                "picked_batch_ids": ln.picked,
                "allocations": ln.allocations,
                "shortfall": ln.left,
            })
        entries_out.append({
            "entry_id": e.id, "plan_id": e.meal_plan_id,
            "plan_name": meta[e.id]["plan_name"], "plan_type": meta[e.id]["plan_type"],
            "scheduled_date": e.scheduled_date, "meal_type": e.meal_type,
            "recipe_name": meta[e.id]["recipe_name"], "servings": e.servings,
            "lines": lines_out,
        })

    batches_out = []
    for b in batches:
        allocs = sorted(batch_allocs.get(b.id, []), key=lambda a: order[a["entry_id"]])
        reserved = sum((a["amount"] for a in allocs), _ZERO)
        batches_out.append({
            "batch_id": b.id, "ingredient_id": b.ingredient_id,
            "quantity": b.quantity_grams, "reserved": reserved,
            "free": b.quantity_grams - reserved,
            "expired": is_expired(b.expires_at, today),
            "allocations": allocs,
        })

    # 食材名 + 规范单位(批次 / 需求涉及的全部食材; 前端不必再分页拉 /ingredients)
    ing_ids = {b.ingredient_id for b in batches} | {
        i for per in lines.values() for i in per
    }
    ingredients = {}
    if ing_ids:
        for ing in (await db.execute(
            select(Ingredient).where(Ingredient.id.in_(ing_ids))
        )).scalars().all():
            ingredients[ing.id] = {"name": ing.name, "unit": ing.nutrition_basis_unit or "g"}

    return {
        "today": today,
        "batches": batches_out,
        "entries": entries_out,
        "shortfalls": [
            {"ingredient_id": i, "amount": v}
            for i, v in sorted(shortfall_by_ing.items())
        ],
        "ingredients": ingredients,
    }


def hard_reserved(reservations: dict) -> dict[int, Decimal]:
    """每个批次被「手选」硬预留的量(真实扣减时要让开这部分)。"""
    out: dict[int, Decimal] = defaultdict(lambda: _ZERO)
    for b in reservations["batches"]:
        for a in b["allocations"]:
            if a["manual"]:
                out[b["batch_id"]] += a["amount"]
    return out
