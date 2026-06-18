from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ---------- 身体数据(N4: PUT body-metrics) ----------

class BodyMetricsUpdate(BaseModel):
    """提交身体数据 → 存 users 表。全可选(允许部分更新),但算目标前需填齐。"""
    height_cm: Decimal | None = Field(default=None, gt=0, le=300)
    weight_kg: Decimal | None = Field(default=None, gt=0, le=700)
    age: int | None = Field(default=None, ge=1, le=150)
    biological_sex: str | None = None      # male/female/other
    activity_level: str | None = None      # sedentary/light/moderate/active/very_active


class BodyMetricsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    height_cm: Decimal | None
    weight_kg: Decimal | None
    age: int | None
    biological_sex: str | None
    activity_level: str | None


# ---------- 营养目标计算(N4: POST nutrition-goal/compute) ----------

class NutritionGoalCompute(BaseModel):
    """按当前身体数据算目标。goal_type 必填; calorie_delta 可选(覆盖默认增减)。"""
    goal_type: str = Field(pattern="^(fat_loss|muscle_gain|maintenance)$")
    calorie_delta: Decimal | None = None


# ---------- 手动覆盖(N4: PUT nutrition-goal) ----------

class NutritionGoalOverride(BaseModel):
    """用户手动指定四个 daily 值, 存为 is_custom=True。"""
    goal_type: str = Field(pattern="^(fat_loss|muscle_gain|maintenance)$")
    daily_calories: Decimal = Field(gt=0)
    daily_protein_g: Decimal = Field(ge=0)
    daily_carbs_g: Decimal = Field(ge=0)
    daily_fat_g: Decimal = Field(ge=0)


# ---------- 读取(N4: GET nutrition-goal) ----------

class NutritionGoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    goal_type: str
    daily_calories: Decimal
    daily_protein_g: Decimal
    daily_carbs_g: Decimal
    daily_fat_g: Decimal
    is_custom: bool