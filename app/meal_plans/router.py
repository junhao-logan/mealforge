from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.schemas import MealPlanGenerateRequest
from app.ai.services import (
    AiError,
    EmptyRecipeCatalogError,
    RecipeValidationError,
    generate_meal_plan,
)
from app.auth.dependencies import get_current_user
from app.core.cache import cache_get, cache_set, invalidate_summary, summary_key
from app.core.database import get_db
from app.core.redis import get_redis
from app.inventory import services as inventory_services
from app.meal_plans.models import MealPlan, MealPlanEntry
from app.meal_plans.schemas import (
    CalendarEntryRead,
    DailySummaryRead,
    EntryCompleteRead,
    MacroSummary,
    MealPlanCreate,
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
from app.recipes.models import Recipe, RecipeVariant
from app.users.models import User

router = APIRouter(prefix="/meal-plans", tags=["meal-plans"])


@router.post("/generate", response_model=MealPlanRead, status_code=201)
async def generate_meal_plan_endpoint(
    payload: MealPlanGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MealPlan:
    """AI 从已有可见菜谱排布周计划(Week 8)。无可用菜谱 400; AI 失败 502。"""
    start = payload.start_date or date.today()
    try:
        plan = await generate_meal_plan(
            db, user, start_date=start, days=payload.days,
            meals=payload.meals, free_text=payload.free_text,
        )
    except EmptyRecipeCatalogError as e:
        raise HTTPException(400, str(e)) from e
    except (AiError, RecipeValidationError) as e:
        raise HTTPException(502, "AI 生成暂时不可用, 请稍后重试") from e

    loaded = (await db.execute(
        select(MealPlan)
        .where(MealPlan.id == plan.id)
        .options(selectinload(MealPlan.entries))
    )).scalar_one()
    # 失效计划覆盖的每一天(start..end)
    await invalidate_summary(redis, user.id, *_dates_in(loaded.start_date, loaded.end_date))
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

    if not (plan.start_date <= payload.scheduled_date <= plan.end_date):
        raise HTTPException(
            422,
            f"日期 {payload.scheduled_date} 超出计划范围 "
            f"({plan.start_date} ~ {plan.end_date})",
        )

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