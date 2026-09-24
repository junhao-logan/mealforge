from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.schemas import MealPlanGenerateRequest
from app.ai.services import (
    AiError,
    EmptyRecipeCatalogError,
    RecipeValidationError,
    generate_meal_plan,
    persist_new_recipe,
)
from app.auth.dependencies import get_current_user
from app.core.cache import cache_get, cache_set, invalidate_summary, summary_key
from app.core.database import get_db
from app.core.redis import get_redis
from app.inventory import services as inventory_services
from app.inventory.models import EntryBatchPick, InventoryItem
from app.inventory.reservations import compute_reservations
from app.inventory.schemas import EntryPicksUpdate
from app.meal_plans.models import MealPlan, MealPlanEntry
from app.meal_plans.schemas import (
    CalendarEntryRead,
    DailySummaryRead,
    EntryCompleteRead,
    MacroSummary,
    MealPlanCommitRequest,
    MealPlanCreate,
    MealPlanDraft,
    MealPlanEntryCreate,
    MealPlanEntryRead,
    MealPlanListItem,
    MealPlanRead,
    QuickLogCreate,
    ShortfallItem,
)
from app.meal_plans.services import (
    expand_plan_range,
    get_or_create_default_plan,
    meal_type_sort_key,
)
from app.nutrition.models import UserNutritionGoal
from app.recipes.models import Recipe, RecipeIngredient, RecipeVariant
from app.users.models import User

router = APIRouter(prefix="/meal-plans", tags=["meal-plans"])


@router.post("/generate", response_model=MealPlanDraft)
async def generate_meal_plan_endpoint(
    payload: MealPlanGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """AI 排布周计划 → 返回**草稿**(不落库)。用户预览确认后再调 /generate/commit。
    无可用菜谱 400; AI 失败 502。阶段A 仅支持 recipe_source='existing'。
    """
    start = payload.start_date or date.today()
    try:
        return await generate_meal_plan(
            db, user, start_date=start, days=payload.days,
            meals=payload.meals, free_text=payload.free_text,
            ingredient_source=payload.ingredient_source,
            recipe_source=payload.recipe_source, language=payload.language,
        )
    except EmptyRecipeCatalogError as e:
        raise HTTPException(400, str(e)) from e
    except (AiError, RecipeValidationError) as e:
        raise HTTPException(502, "AI 生成暂时不可用, 请稍后重试") from e


@router.post("/generate/commit", response_model=MealPlanRead, status_code=201)
async def commit_meal_plan_draft(
    payload: MealPlanCommitRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MealPlan:
    """确认草稿 → 把(用户已调整的)餐次**追加**进目标计划。
    target_plan_id=None → 新建 ai_generated 计划; 否则追加进该计划(校验归属)。
    校验每个 variant 对用户可见(防越权引用); 追加不清空原有 entries。
    """
    start = payload.start_date

    # 1) 目标计划: 追加进已有 / 新建
    if payload.target_plan_id is not None:
        plan = await _get_owned_plan(db, payload.target_plan_id, user)
    else:
        end = start + timedelta(days=max(e.day_offset for e in payload.entries))
        plan = MealPlan(
            user_id=user.id, start_date=start, end_date=end,
            plan_type="ai_generated",
        )
        db.add(plan)
        await db.flush()

    # 2) 校验已有做法的 variant 对用户可见(global 或本人私有)
    existing_ids = {e.recipe_variant_id for e in payload.entries if e.new_recipe is None}
    if existing_ids:
        visible = set((await db.execute(
            select(RecipeVariant.id)
            .join(Recipe, Recipe.id == RecipeVariant.recipe_id)
            .where(
                RecipeVariant.id.in_(existing_ids),
                or_(Recipe.visibility == "global", Recipe.created_by_user_id == user.id),
            )
        )).scalars().all())
        missing = existing_ids - visible
        if missing:
            raise HTTPException(400, f"引用了不可见的菜谱做法: {sorted(missing)}")

    # 3) 逐条追加 entry; new_recipe → 现在才落库(去重食材 + 建菜谱), 按需撑大日期范围
    affected: set[date] = set()
    try:
        for e in payload.entries:
            if e.new_recipe is not None:
                variant_id = await persist_new_recipe(db, user, e.new_recipe.model_dump())
            elif e.recipe_variant_id is not None:
                variant_id = e.recipe_variant_id
            else:
                raise HTTPException(400, "每条 entry 需给 recipe_variant_id 或 new_recipe")
            sched = start + timedelta(days=e.day_offset)
            expand_plan_range(plan, sched)
            db.add(MealPlanEntry(
                meal_plan_id=plan.id,
                scheduled_date=sched,
                meal_type=e.meal_type,
                recipe_variant_id=variant_id,
                servings=e.servings,
            ))
            affected.add(sched)
    except RecipeValidationError as ex:
        raise HTTPException(400, str(ex)) from ex

    await db.commit()

    loaded = (await db.execute(
        select(MealPlan)
        .where(MealPlan.id == plan.id)
        .options(selectinload(MealPlan.entries))
    )).scalar_one()
    await invalidate_summary(redis, user.id, *affected)
    return loaded


def _dates_in(start: date, end: date) -> list[date]:
    """start..end(含两端)的每一天 —— 多天计划失效缓存用。"""
    n = (end - start).days
    return [start + timedelta(days=i) for i in range(n + 1)]


async def _get_owned_plan(
    db: AsyncSession, plan_id: int, user: User, *, with_entries: bool = False
) -> MealPlan:
    """取计划并校验归属(P4-3): 不是当前用户的 → 404(不泄漏存在性)。"""
    stmt = select(MealPlan).where(MealPlan.id == plan_id)
    if with_entries:
        stmt = stmt.options(selectinload(MealPlan.entries))
    plan = (await db.execute(stmt)).scalar_one_or_none()
    if plan is None or plan.user_id != user.id:
        raise HTTPException(404, f"计划 id={plan_id} 不存在")
    return plan


def _sorted_entries(plan: MealPlan) -> list[MealPlanEntry]:
    """按 (日期, 餐次自定义序, sort_order) 排序 —— 不能靠 meal_type 字母序。"""
    return sorted(
        plan.entries,
        key=lambda e: (e.scheduled_date, meal_type_sort_key(e.meal_type), e.sort_order),
    )


async def _get_owned_entry(
    db: AsyncSession, plan_id: int, entry_id: int, user: User
) -> MealPlanEntry:
    """取 entry 并校验归属(经 plan 关联 user)。"""
    plan = await _get_owned_plan(db, plan_id, user)
    entry = await db.get(MealPlanEntry, entry_id)
    if entry is None or entry.meal_plan_id != plan.id:
        raise HTTPException(404, f"餐次 id={entry_id} 不存在")
    return entry


# ---------- 计划 CRUD ----------

@router.post("", response_model=MealPlanRead, status_code=201)
async def create_plan(
    payload: MealPlanCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MealPlanRead:
    if payload.end_date < payload.start_date:
        raise HTTPException(422, "end_date 不能早于 start_date")

    plan = MealPlan(
        user_id=user.id, name=payload.name,
        start_date=payload.start_date, end_date=payload.end_date,
        plan_type=payload.plan_type, is_template=payload.is_template,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return MealPlanRead.model_validate(
        {**plan.__dict__, "entries": []}
    )


@router.get("", response_model=list[MealPlanListItem])
async def list_plans(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[MealPlan]:
    # 保证用户永远有一个默认 plan(Quick Log): 没有就建, 幂等。
    # 前端删不了默认 plan(见 delete_plan 守卫), 但历史用户可能没有, 这里兜底。
    await get_or_create_default_plan(db, user.id)
    await db.commit()
    stmt = (
        select(MealPlan)
        .where(MealPlan.user_id == user.id)
        .order_by(MealPlan.start_date.desc())
        .offset(skip).limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


# ---------- 每日营养汇总(静态路径, 必须在 /{plan_id} 之前注册) ----------
# ⚠️ 路由顺序: /daily-summary 是静态路径, 若排在 /{plan_id:int} 之后本可匹配,
#    但用 {plan_id:int} 约束后动态路由只吃整数, 静态路径不会被遮蔽。双保险。

@router.get("/entries", response_model=list[CalendarEntryRead])
async def list_entries_in_range(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    start: date = Query(...),
    end: date = Query(...),
) -> list[CalendarEntryRead]:
    """日历视图数据源: 某用户在 [start, end] 内、跨所有 plan 的餐次。

    一次查询带出菜名(join recipe/variant), 前端各视图(天/周/月)共用。
    无 N+1: 单查询 join。按日期→餐次序→sort_order 排序。
    """
    stmt = (
        select(
            MealPlanEntry.id, MealPlan.id,
            MealPlanEntry.scheduled_date, MealPlanEntry.meal_type,
            MealPlanEntry.sort_order, MealPlanEntry.recipe_variant_id,
            Recipe.id, Recipe.name, RecipeVariant.name,
            MealPlanEntry.servings, MealPlanEntry.is_completed,
        )
        .join(MealPlan, MealPlanEntry.meal_plan_id == MealPlan.id)
        .join(RecipeVariant, RecipeVariant.id == MealPlanEntry.recipe_variant_id)
        .join(Recipe, Recipe.id == RecipeVariant.recipe_id)
        .where(
            MealPlan.user_id == user.id,
            MealPlanEntry.scheduled_date >= start,
            MealPlanEntry.scheduled_date <= end,
        )
    )
    rows = (await db.execute(stmt)).all()
    items = [
        CalendarEntryRead(
            id=r[0], plan_id=r[1], scheduled_date=r[2], meal_type=r[3],
            sort_order=r[4], recipe_variant_id=r[5], recipe_id=r[6],
            recipe_name=r[7], variant_name=r[8], servings=r[9], is_completed=r[10],
        )
        for r in rows
    ]
    # 排序: 日期 → 餐次自定义序 → sort_order
    items.sort(key=lambda e: (e.scheduled_date, meal_type_sort_key(e.meal_type), e.sort_order))
    return items


@router.get("/daily-summary", response_model=DailySummaryRead)
async def daily_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    date_: date = Query(..., alias="date"),  # 必填, URL 里叫 date
) -> DailySummaryRead:
    # ── Cache-Aside: 先查缓存, 命中直接返回, 跳过下面的查询+聚合 ──
    cache_key = summary_key(user.id, date_)
    cached = await cache_get(redis, cache_key)   # Redis 出错会返回 None(降级)
    if cached is not None:
        return DailySummaryRead.model_validate(cached)   # 命中: 反序列化直接返回

    # ── 未命中: 走原有的查询 + 聚合 ──
    stmt = (
        select(MealPlanEntry)
        .join(MealPlan, MealPlanEntry.meal_plan_id == MealPlan.id)
        .where(MealPlan.user_id == user.id, MealPlanEntry.scheduled_date == date_)
        .options(selectinload(MealPlanEntry.recipe_variant))
    )
    entries = list((await db.execute(stmt)).scalars().all())

    sums: dict[str, Decimal | None] = {
        "calories": Decimal("0"), "protein": Decimal("0"),
        "carbs": Decimal("0"), "fat": Decimal("0"),
    }
    variant_fields = {
        "calories": "total_calories", "protein": "total_protein_g",
        "carbs": "total_carbs_g", "fat": "total_fat_g",
    }
    for e in entries:
        v = e.recipe_variant
        for key, col in variant_fields.items():
            if sums[key] is None:
                continue
            val = getattr(v, col)
            if val is None:
                sums[key] = None
            else:
                sums[key] += val * e.servings

    goal = (await db.execute(
        select(UserNutritionGoal).where(UserNutritionGoal.user_id == user.id)
    )).scalar_one_or_none()

    def macro(consumed, target):
        pct = None
        if consumed is not None and target is not None and target != 0:
            pct = (consumed / target * Decimal("100")).quantize(Decimal("0.1"))
        return MacroSummary(consumed=consumed, target=target, percent=pct)

    result = DailySummaryRead(
        date=date_,
        entry_count=len(entries),
        calories=macro(sums["calories"], goal.daily_calories if goal else None),
        protein_g=macro(sums["protein"], goal.daily_protein_g if goal else None),
        carbs_g=macro(sums["carbs"], goal.daily_carbs_g if goal else None),
        fat_g=macro(sums["fat"], goal.daily_fat_g if goal else None),
        has_goal=goal is not None,
    )

    # ── 算完存缓存(存不了不影响返回); 序列化成 JSON 友好格式 ──
    await cache_set(redis, cache_key, result.model_dump(mode="json"))
    return result


# ---------- 快捷记录(记录型用户, 无感 default plan) ----------

@router.post("/quick-log", response_model=MealPlanEntryRead, status_code=201)
async def quick_log(
    payload: QuickLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MealPlanEntry:
    variant = await db.get(RecipeVariant, payload.recipe_variant_id)
    if variant is None:
        raise HTTPException(404, f"菜谱版本 id={payload.recipe_variant_id} 不存在")

    d = payload.scheduled_date or date.today()

    plan = await get_or_create_default_plan(db, user.id)
    expand_plan_range(plan, d)

    entry = MealPlanEntry(
        meal_plan_id=plan.id,
        scheduled_date=d,
        meal_type=payload.meal_type,
        recipe_variant_id=payload.recipe_variant_id,
        servings=payload.servings,
        sort_order=0,
        notes=payload.notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    await invalidate_summary(redis, user.id, d)   # 该天营养变了 → 失效缓存
    return entry


# ---------- 单个计划(动态路径, {plan_id:int} 只匹配整数, 避免遮蔽静态路径) ----------

@router.get("/{plan_id:int}", response_model=MealPlanRead)
async def get_plan(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MealPlanRead:
    plan = await _get_owned_plan(db, plan_id, user, with_entries=True)
    return MealPlanRead.model_validate({
        **plan.__dict__,
        "entries": [
            MealPlanEntryRead.model_validate(e) for e in _sorted_entries(plan)
        ],
    })


@router.delete("/{plan_id:int}", status_code=204)
async def delete_plan(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    plan = await _get_owned_plan(db, plan_id, user)
    # 默认 plan(Quick Log)是系统级收纳计划, 不可删除(前端也不显示删除按钮, 这里硬兜底)
    if plan.plan_type == "default":
        raise HTTPException(400, "默认计划(Quick Log)不可删除")
    days = _dates_in(plan.start_date, plan.end_date)   # 删前记下覆盖的天
    await db.delete(plan)
    await db.commit()
    await invalidate_summary(redis, user.id, *days)


# ---------- 计划里的 entry ----------

@router.post("/{plan_id:int}/entries", response_model=MealPlanEntryRead, status_code=201)
async def add_entry(
    plan_id: int,
    payload: MealPlanEntryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MealPlanEntry:
    plan = await _get_owned_plan(db, plan_id, user)

    # 日期超出 plan 范围 → 自动扩展(与 quick-log 一致, 统一排餐行为)
    expand_plan_range(plan, payload.scheduled_date)

    variant = await db.get(RecipeVariant, payload.recipe_variant_id)
    if variant is None:
        raise HTTPException(404, f"菜谱版本 id={payload.recipe_variant_id} 不存在")

    entry = MealPlanEntry(
        meal_plan_id=plan.id,
        scheduled_date=payload.scheduled_date,
        meal_type=payload.meal_type,
        recipe_variant_id=payload.recipe_variant_id,
        servings=payload.servings,
        sort_order=payload.sort_order,
        notes=payload.notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    await invalidate_summary(redis, user.id, payload.scheduled_date)  # 失效该天
    return entry


@router.delete("/{plan_id:int}/entries/{entry_id}", status_code=204)
async def delete_entry(
    plan_id: int,
    entry_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    plan = await _get_owned_plan(db, plan_id, user)
    entry = await db.get(MealPlanEntry, entry_id)
    if entry is None or entry.meal_plan_id != plan.id:
        raise HTTPException(404, f"餐次 id={entry_id} 不存在")
    affected_date = entry.scheduled_date          # 删前记下日期(删后取不到)
    await db.delete(entry)
    await db.commit()
    await invalidate_summary(redis, user.id, affected_date)  # 失效该天


@router.patch("/{plan_id:int}/entries/{entry_id}/complete", response_model=EntryCompleteRead)
async def complete_entry(
    plan_id: int,
    entry_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> EntryCompleteRead:
    """标记完成 + 按 FEFO 扣减库存(同事务)。
    库存不足不阻止完成(I1/决策①): 短缺只作为信息返回。
    """
    entry = await _get_owned_entry(db, plan_id, entry_id, user)

    if entry.is_completed:
        return EntryCompleteRead(
            entry=MealPlanEntryRead.model_validate(entry),
            shortfalls=[],
        )

    entry.is_completed = True
    entry.completed_at = datetime.now(UTC)

    shortfalls = await inventory_services.deduct_for_entry(db, user.id, entry)

    await db.commit()
    await db.refresh(entry)
    await invalidate_summary(redis, user.id, entry.scheduled_date)  # 失效该天

    return EntryCompleteRead(
        entry=MealPlanEntryRead.model_validate(entry),
        shortfalls=[ShortfallItem(**s) for s in shortfalls],
    )


@router.patch("/{plan_id:int}/entries/{entry_id}/uncomplete", response_model=MealPlanEntryRead)
async def uncomplete_entry(
    plan_id: int,
    entry_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MealPlanEntry:
    """撤销完成 + 把完成时扣的库存退回原批次(同事务, I2)。
    幂等: 未完成的 entry 直接返回, 不重复回补。
    """
    entry = await _get_owned_entry(db, plan_id, entry_id, user)

    if not entry.is_completed:
        return entry                      # 本就未完成, 无需回补

    entry.is_completed = False
    entry.completed_at = None

    await inventory_services.restock_for_entry(db, user.id, entry)

    await db.commit()
    await db.refresh(entry)
    await invalidate_summary(redis, user.id, entry.scheduled_date)  # 失效该天

    return entry

@router.put("/{plan_id:int}/entries/{entry_id}/picks", status_code=204)
async def set_entry_picks(
    plan_id: int,
    entry_id: int,
    payload: EntryPicksUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """A4: 设定某餐某食材用哪几批(按列表顺序取够, 不够的部分仍自动分配)。
    只能选「还没被其他餐次预留」的余量(本餐自己当前占的也算可选)。过期批次可手选。
    空列表 = 清掉手选, 恢复自动分配。整组替换, 不做增量。
    """
    entry = await _get_owned_entry(db, plan_id, entry_id, user)
    if entry.is_completed:
        raise HTTPException(400, "Meal already completed; batches can no longer be changed")

    ids = payload.inventory_item_ids
    if len(set(ids)) != len(ids):
        raise HTTPException(400, "Duplicate batch in selection")

    in_recipe = (await db.execute(
        select(RecipeIngredient.id).where(
            RecipeIngredient.recipe_variant_id == entry.recipe_variant_id,
            RecipeIngredient.ingredient_id == payload.ingredient_id,
        ).limit(1)
    )).scalar_one_or_none()
    if in_recipe is None:
        raise HTTPException(400, "Ingredient is not used by this meal")

    if ids:
        items = {
            it.id: it for it in (await db.execute(
                select(InventoryItem).where(InventoryItem.id.in_(ids))
            )).scalars().all()
        }
        # 可选量 = 批次未预留 + 本餐当前从它取的(与前端显示同一口径)
        res = await compute_reservations(db, user.id)
        free = {b["batch_id"]: b["free"] for b in res["batches"]}
        own: dict[int, Decimal] = {}
        for e in res["entries"]:
            if e["entry_id"] != entry.id:
                continue
            for ln in e["lines"]:
                if ln["ingredient_id"] == payload.ingredient_id:
                    for a in ln["allocations"]:
                        own[a["batch_id"]] = own.get(a["batch_id"], Decimal("0")) + a["amount"]
        for bid in ids:
            it = items.get(bid)
            if (it is None or it.user_id != user.id
                    or it.ingredient_id != payload.ingredient_id):
                raise HTTPException(400, f"Batch {bid} is not available for this ingredient")
            if free.get(bid, Decimal("0")) + own.get(bid, Decimal("0")) <= 0:
                raise HTTPException(400, f"Batch {bid} is fully reserved by other meals")

    await db.execute(delete(EntryBatchPick).where(
        EntryBatchPick.entry_id == entry.id,
        EntryBatchPick.ingredient_id == payload.ingredient_id,
    ))
    for pos, bid in enumerate(ids):
        db.add(EntryBatchPick(
            entry_id=entry.id, ingredient_id=payload.ingredient_id,
            inventory_item_id=bid, position=pos,
        ))
    await db.commit()
