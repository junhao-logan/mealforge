from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# 餐段取值(排序见 services.MEAL_TYPE_ORDER)。所有写入口共用, 防止 "brunch" 之类脏值入库
MEAL_TYPE_PATTERN = "^(breakfast|lunch|dinner|snack)$"
# 数量上限: 远低于 Numeric(10,2) / Numeric(8,2) 的列上限, 超出直接 422 而不是入库时 500
AMOUNT_MAX = 100_000

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
    meal_type: str = Field(pattern=MEAL_TYPE_PATTERN)
    recipe_variant_id: int
    servings: Decimal = Field(default=Decimal("1.0"), gt=0, le=50)
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


class CalendarEntryRead(BaseModel):
    """日历视图用: 餐次 + 冗余菜名/recipe_id(前端显示&跳详情)+ 所属 plan。
    避免前端 N+1 查菜名。"""
    id: int
    plan_id: int
    scheduled_date: date
    meal_type: str
    sort_order: int
    recipe_variant_id: int
    recipe_id: int
    recipe_name: str
    variant_name: str
    servings: Decimal
    is_completed: bool


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
    meal_type: str = Field(pattern=MEAL_TYPE_PATTERN)
    recipe_variant_id: int
    servings: Decimal = Field(default=Decimal("1.0"), gt=0, le=50)
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

class ShortfallItem(BaseModel):
    """完成餐次时某食材的短缺(库存不足部分)。"""
    ingredient_id: int
    shortfall_grams: Decimal


class RestockLoss(BaseModel):
    """退回库存时退不回去的部分(原批次已被删除, A5)。"""
    ingredient_id: int
    name: str | None
    unit: str
    amount: Decimal


class RestockResult(BaseModel):
    """删除餐次 / 计划的响应: 退不回去的部分(没选退回或没有可退的就是空列表)。"""
    unrestorable: list[RestockLoss] = []


class EntryUncompleteRead(BaseModel):
    """撤销完成的响应: entry + 退不回去的部分(A5)。"""
    entry: MealPlanEntryRead
    unrestorable: list[RestockLoss] = []


class EntryCompleteRead(BaseModel):
    """完成餐次的响应: entry + 本次扣减产生的短缺(I1: 短缺另记,不写回库存)。"""
    entry: MealPlanEntryRead
    shortfalls: list[ShortfallItem]

# ---------- AI 周计划: 草稿(生成) + 提交(确认) ----------

class NewRecipeIngredient(BaseModel):
    """现编菜谱的一条配料: 引用已有食材(ingredient_id) 或 新建(new_name)。
    两个都给时以 ingredient_id 为准(AI 常把名字也带上); 落库逻辑同样优先用 id。"""
    ingredient_id: int | None = None
    new_name: str | None = Field(default=None, max_length=100)
    amount: Decimal = Field(gt=0, le=AMOUNT_MAX)   # 已有食材用其单位; 新食材用克
    per100g: dict | None = None                    # 仅新食材: AI 估每 100g 营养

    @field_validator("new_name", mode="before")
    @classmethod
    def _blank_name_is_none(cls, v):
        return v.strip() or None if isinstance(v, str) else v

    @model_validator(mode="after")
    def _has_source(self):
        # 两个都缺: 落库时 None.lower() → 500
        if self.ingredient_id is None and self.new_name is None:
            raise ValueError("每条配料需提供 ingredient_id 或 new_name")
        return self


class NewRecipeDraft(BaseModel):
    """AI 现编的新菜谱(确认后才入库)。"""
    name: str
    instructions: str
    cuisine: str | None = None
    servings: Decimal | None = Field(default=None, gt=0, le=50)
    ingredients: list[NewRecipeIngredient] = Field(min_length=1)


class MealPlanDraftEntry(BaseModel):
    """草稿里的一条餐次: 已有 → recipe_variant_id; 现编 → is_new + new_recipe。"""
    day_offset: int
    meal_type: str
    servings: Decimal = Decimal("1")
    recipe_name: str
    is_new: bool = False
    recipe_variant_id: int | None = None
    variant_name: str | None = None
    new_recipe: NewRecipeDraft | None = None


class MealPlanDraft(BaseModel):
    """AI 生成的草稿: 不落库, 前端预览/调整后再 commit。"""
    start_date: date
    days: int
    meals: list[str]
    entries: list[MealPlanDraftEntry]


class MealPlanCommitEntry(BaseModel):
    """确认时提交的一条餐次: 用已有 variant 或现编 new_recipe(二选一, 确认时才落库)。"""
    day_offset: int = Field(ge=0, le=13)            # 与生成上限 days ≤ 14 对齐
    meal_type: str = Field(pattern=MEAL_TYPE_PATTERN)
    servings: Decimal = Field(default=Decimal("1"), gt=0, le=50)
    recipe_variant_id: int | None = None
    new_recipe: NewRecipeDraft | None = None

    @model_validator(mode="after")
    def _one_source(self):
        # 两个都缺: 之前会把 None 放进待校验集合, 排序时 TypeError → 500
        if (self.recipe_variant_id is None) == (self.new_recipe is None):
            raise ValueError("每条餐次需且只需提供 recipe_variant_id 或 new_recipe 之一")
        return self


class MealPlanCommitRequest(BaseModel):
    """确认草稿 → 追加进目标计划(target_plan_id=None 则新建 ai_generated 计划)。"""
    target_plan_id: int | None = None
    start_date: date
    entries: list[MealPlanCommitEntry] = Field(min_length=1)
