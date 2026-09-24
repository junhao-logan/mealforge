from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.cache import invalidate_all_summaries
from app.core.database import get_db
from app.core.redis import get_redis
from app.nutrition.models import UserNutritionGoal
from app.nutrition.schemas import (
    BodyMetricsRead,
    BodyMetricsUpdate,
    NutritionGoalCompute,
    NutritionGoalOverride,
    NutritionGoalRead,
)
from app.nutrition.services import compute_nutrition_goal
from app.users.models import User

router = APIRouter(prefix="/users/me", tags=["nutrition"])


# ---------- 身体数据 ----------

@router.put("/body-metrics", response_model=BodyMetricsRead)
async def update_body_metrics(
    payload: BodyMetricsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    # 部分更新: 只覆盖本次传了的字段(None 表示不改)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


# ---------- 算营养目标(按身体数据) ----------

@router.post("/nutrition-goal/compute", response_model=NutritionGoalRead)
async def compute_goal(
    payload: NutritionGoalCompute,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> UserNutritionGoal:
    # 算之前必须身体数据填齐
    missing = [
        f for f in ("height_cm", "weight_kg", "age", "biological_sex", "activity_level")
        if getattr(user, f) is None
    ]
    if missing:
        raise HTTPException(
            422, f"请先补全身体数据后再计算目标, 缺少: {', '.join(missing)}"
        )

    result = compute_nutrition_goal(
        weight_kg=user.weight_kg, height_cm=user.height_cm, age=user.age,
        biological_sex=user.biological_sex, activity_level=user.activity_level,
        goal_type=payload.goal_type, calorie_delta=payload.calorie_delta,
    )

    # upsert: 一个用户一条目标(user_id unique), 重算覆盖旧的
    goal = await _upsert_goal(
        db, user.id, payload.goal_type, result, is_custom=False
    )
    # 每日汇总缓存里带着目标与达成率, 目标变了要全部失效(否则最多旧 1 小时)
    await invalidate_all_summaries(redis, user.id)
    return goal


# ---------- 手动覆盖 ----------

@router.put("/nutrition-goal", response_model=NutritionGoalRead)
async def override_goal(
    payload: NutritionGoalOverride,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> UserNutritionGoal:
    values = {
        "daily_calories": payload.daily_calories,
        "daily_protein_g": payload.daily_protein_g,
        "daily_carbs_g": payload.daily_carbs_g,
        "daily_fat_g": payload.daily_fat_g,
    }
    goal = await _upsert_goal(
        db, user.id, payload.goal_type, values, is_custom=True
    )
    await invalidate_all_summaries(redis, user.id)
    return goal


# ---------- 读取 ----------

@router.get("/nutrition-goal", response_model=NutritionGoalRead)
async def get_goal(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserNutritionGoal:
    goal = (await db.execute(
        select(UserNutritionGoal).where(UserNutritionGoal.user_id == user.id)
    )).scalar_one_or_none()
    if goal is None:
        raise HTTPException(404, "尚未设置营养目标")
    return goal


# ---------- 内部: upsert 目标 ----------

async def _upsert_goal(db, user_id, goal_type, values: dict, *, is_custom: bool):
    """一个用户一条目标(user_id unique)。存在则更新, 否则插入。"""
    stmt = insert(UserNutritionGoal).values(
        user_id=user_id, goal_type=goal_type, is_custom=is_custom, **values,
    ).on_conflict_do_update(
        index_elements=["user_id"],
        # 更新分支也要刷新 updated_at(onupdate 只对 ORM UPDATE 生效, 对 upsert 不生效)
        set_={"goal_type": goal_type, "is_custom": is_custom, **values, "updated_at": func.now()},
    ).returning(UserNutritionGoal)
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()