from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ---------- 计划 ----------

class MealPlanCreate(BaseModel):
    """建计划(空壳, 不带 entry)。"""
    name: str | None = Field(default=None, max_length=100)
    start_date: date
    end_date: date
    plan_type: str = Field(default="regular", pattern="^(regular|template|special)$")
    is_template: bool = False


class MealPlanListItem(BaseModel):
    """列表项(精简, 不嵌套 entry)。"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str | None
    start_date: date
    end_date: date
    plan_type: str
    is_template: bool


# ---------- 餐次 entry ----------

class MealPlanEntryCreate(BaseModel):
    """往计划加一条 entry。"""
    scheduled_date: date
    meal_type: str = Field(pattern="^(breakfast|lunch|dinner|snack)$")
    recipe_variant_id: int
    servings: Decimal = Field(default=Decimal("1.0"), gt=0)
    sort_order: int = Field(default=0, ge=0)
    notes: str | None = None


class MealPlanEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scheduled_date: date
    meal_type: str
    sort_order: int
    recipe_variant_id: int
    servings: Decimal
    is_completed: bool
    completed_at: datetime | None
    notes: str | None


class MealPlanRead(BaseModel):
    """计划详情(含扁平排序的 entry 列表)。"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str | None
    start_date: date
    end_date: date
    plan_type: str
    is_template: bool
    entries: list[MealPlanEntryRead]


# ---------- 快捷记录 ----------

class QuickLogCreate(BaseModel):
    """快捷记录一餐 → 自动进 default plan。date 默认今天。"""
    scheduled_date: date | None = None  # None = 今天(router 里填)
    meal_type: str = Field(pattern="^(breakfast|lunch|dinner|snack)$")
    recipe_variant_id: int
    servings: Decimal = Field(default=Decimal("1.0"), gt=0)
    notes: str | None = None


# ---------- 每日汇总 ----------

class MacroSummary(BaseModel):
    """某项营养的汇总: 实际摄入 vs 目标 vs 达标率。"""
    consumed: Decimal | None       # 实际(NULL=含未知营养, 不完整)
    target: Decimal | None         # 目标(NULL=用户没设目标)
    percent: Decimal | None        # 达标率 %(consumed/target×100), 任一为 NULL 则 NULL


class DailySummaryRead(BaseModel):
    """某用户某天的营养汇总(跨所有 plan)。"""
    date: date
    entry_count: int               # 当天有几条 entry
    calories: MacroSummary
    protein_g: MacroSummary
    carbs_g: MacroSummary
    fat_g: MacroSummary
    has_goal: bool                 # 用户是否设了营养目标