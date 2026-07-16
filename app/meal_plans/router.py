from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.users.models import User
from app.recipes.models import RecipeVariant
from app.meal_plans.models import MealPlan, MealPlanEntry
from app.meal_plans.schemas import (
    MealPlanCreate, MealPlanRead, MealPlanListItem,
    MealPlanEntryCreate, MealPlanEntryRead,
)
from app.meal_plans.services import meal_type_sort_key

from app.nutrition.models import UserNutritionGoal
from app.meal_plans.schemas import QuickLogCreate, DailySummaryRead, EntryCompleteRead, ShortfallItem
from app.meal_plans.services import (
    get_or_create_default_plan, expand_plan_range, meal_type_sort_key,  # meal_type_sort_key 已import则不重复
)
from app.inventory import services as inventory_services
from datetime import date, datetime, timezone
from decimal import Decimal
router = APIRouter(prefix="/meal-plans", tags=["meal-plans"])


async def _get_owned_plan(
    db: AsyncSession, plan_id: int, user: User, *, with_entries: bool = False
) -> MealPlan:
    """取计划并校验归属(P4-3): 不是当前用户的 → 404(不泄漏存在性)。"""
    stmt = select(MealPlan).where(MealPlan.id == plan_id)
    if with_entries:
        stmt = stmt.options(selectinload(MealPlan.entries))
    plan = (await db.execute(stmt)).scalar_one_or_none()
    # 不存在, 或存在但不属于我 —— 都返回 404(不区分, 防止探测别人的 plan id)
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
    # 应用层校验日期(DB 的 CHECK 是兜底; 这里给友好报错)
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
    # 新建的计划没有 entry, 手动给空列表(避免触发 lazy load)
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


@router.get("/{plan_id}", response_model=MealPlanRead)
async def get_plan(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MealPlanRead:
    plan = await _get_owned_plan(db, plan_id, user, with_entries=True)
    # 手动组装, entry 排好序
    return MealPlanRead.model_validate({
        **plan.__dict__,
        "entries": [
            MealPlanEntryRead.model_validate(e) for e in _sorted_entries(plan)
        ],
    })


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    plan = await _get_owned_plan(db, plan_id, user)
    await db.delete(plan)  # entry 走 CASCADE 一起删
    await db.commit()


# ---------- 计划里的 entry ----------

@router.post("/{plan_id}/entries", response_model=MealPlanEntryRead, status_code=201)
async def add_entry(
    plan_id: int,
    payload: MealPlanEntryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MealPlanEntry:
    plan = await _get_owned_plan(db, plan_id, user)

    # P2-b: entry 日期须在计划范围内(default plan 除外, 但这是显式计划端点)
    if not (plan.start_date <= payload.scheduled_date <= plan.end_date):
        raise HTTPException(
            422,
            f"日期 {payload.scheduled_date} 超出计划范围 "
            f"({plan.start_date} ~ {plan.end_date})",
        )

    # P4-2: 校验 recipe_variant 存在
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
    return entry


@router.delete("/{plan_id}/entries/{entry_id}", status_code=204)
async def delete_entry(
    plan_id: int,
    entry_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    plan = await _get_owned_plan(db, plan_id, user)
    entry = await db.get(MealPlanEntry, entry_id)
    # 校验 entry 确实属于这个 plan(防止跨计划删)
    if entry is None or entry.meal_plan_id != plan.id:
        raise HTTPException(404, f"餐次 id={entry_id} 不存在")
    await db.delete(entry)
    await db.commit()


@router.patch("/{plan_id}/entries/{entry_id}/complete", response_model=EntryCompleteRead)
async def complete_entry(
    plan_id: int,
    entry_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EntryCompleteRead:
    """标记完成 + 按 FEFO 扣减库存(同事务)。
    库存不足不阻止完成(I1/决策①): 短缺只作为信息返回。
    """
    entry = await _get_owned_entry(db, plan_id, entry_id, user)



    # 幂等: 已完成则不重复扣减
    if entry.is_completed:
        return EntryCompleteRead(
            entry=MealPlanEntryRead.model_validate(entry),
            shortfalls=[],
        )

    entry.is_completed = True
    entry.completed_at = datetime.now(timezone.utc)

    # 扣减库存(不 commit, 与上面的完成标记同事务)
    shortfalls = await inventory_services.deduct_for_entry(db, user.id, entry)

    await db.commit()        # ← 完成标记 + 库存扣减 + 流水, 一起生效
    await db.refresh(entry)

    return EntryCompleteRead(
        entry=MealPlanEntryRead.model_validate(entry),
        shortfalls=[ShortfallItem(**s) for s in shortfalls],
    )
# ---------- 快捷记录(记录型用户, 无感 default plan) ----------

@router.post("/quick-log", response_model=MealPlanEntryRead, status_code=201)
async def quick_log(
    payload: QuickLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MealPlanEntry:
    # 校验菜谱版本存在
    variant = await db.get(RecipeVariant, payload.recipe_variant_id)
    if variant is None:
        raise HTTPException(404, f"菜谱版本 id={payload.recipe_variant_id} 不存在")

    # 日期默认今天
    d = payload.scheduled_date or date.today()

    # 取或建 default plan(记录型用户无感)
    plan = await get_or_create_default_plan(db, user.id)
    # 动态撑大 default plan 范围以容纳这条记录
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
    return entry


# ---------- 每日营养汇总(跨所有 plan, vs 目标) ----------

@router.get("/daily-summary", response_model=DailySummaryRead)
async def daily_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    date_: date = Query(..., alias="date"),  # 必填, URL 里叫 date
) -> DailySummaryRead:
    # 1. 查该用户当天所有 entry(跨所有 plan) —— entry 经 plan 关联 user
    #    join meal_plans 过滤 user_id + 该天; 预加载 variant 拿营养缓存
    stmt = (
        select(MealPlanEntry)
        .join(MealPlan, MealPlanEntry.meal_plan_id == MealPlan.id)
        .where(MealPlan.user_id == user.id, MealPlanEntry.scheduled_date == date_)
        .options(selectinload(MealPlanEntry.recipe_variant))
    )
    entries = list((await db.execute(stmt)).scalars().all())

    # 2. 累加营养(variant 缓存营养 × servings); NULL 传播
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
                sums[key] = None  # 某道菜该营养未知 → 当天该项不完整
            else:
                sums[key] += val * e.servings

    # 3. 读用户营养目标
    goal = (await db.execute(
        select(UserNutritionGoal).where(UserNutritionGoal.user_id == user.id)
    )).scalar_one_or_none()

    def macro(consumed, target):
        pct = None
        if consumed is not None and target is not None and target != 0:
            pct = (consumed / target * Decimal("100")).quantize(Decimal("0.1"))
        return MacroSummary(consumed=consumed, target=target, percent=pct)

    return DailySummaryRead(
        date=date_,
        entry_count=len(entries),
        calories=macro(sums["calories"], goal.daily_calories if goal else None),
        protein_g=macro(sums["protein"], goal.daily_protein_g if goal else None),
        carbs_g=macro(sums["carbs"], goal.daily_carbs_g if goal else None),
        fat_g=macro(sums["fat"], goal.daily_fat_g if goal else None),
        has_goal=goal is not None,
    )