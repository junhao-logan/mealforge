from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


# 活动系数(N1: 标准 5 档)
ACTIVITY_FACTORS: dict[str, Decimal] = {
    "sedentary": Decimal("1.2"),
    "light": Decimal("1.375"),
    "moderate": Decimal("1.55"),
    "active": Decimal("1.725"),
    "very_active": Decimal("1.9"),
}

# 目标热量默认增减(N1: 用户可覆盖, 这是默认值)
GOAL_CALORIE_DELTA: dict[str, Decimal] = {
    "fat_loss": Decimal("-500"),
    "maintenance": Decimal("0"),
    "muscle_gain": Decimal("400"),
}

# 宏量参数(N1: 蛋白按体重 / 脂肪按热量百分比 / 碳水填余)
PROTEIN_G_PER_KG = Decimal("2.0")     # 2g/kg 体重
FAT_PCT_OF_CALORIES = Decimal("0.25") # 脂肪占目标热量 25%
# 每克热量: 蛋白/碳水 4 kcal, 脂肪 9 kcal
KCAL_PER_G_PROTEIN = Decimal("4")
KCAL_PER_G_CARB = Decimal("4")
KCAL_PER_G_FAT = Decimal("9")


def _round1(x: Decimal) -> Decimal:
    """四舍五入到 1 位小数(对齐 DB Numeric scale)。"""
    return x.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def compute_bmr(
    weight_kg: Decimal, height_cm: Decimal, age: int, biological_sex: str
) -> Decimal:
    """BMR —— Mifflin-St Jeor (N1)。
    男: 10W + 6.25H − 5A + 5
    女: 10W + 6.25H − 5A − 161
    'other' 取男女常数均值(−78)作折中。
    """
    base = (Decimal("10") * weight_kg
            + Decimal("6.25") * height_cm
            - Decimal("5") * age)
    sex_const = {
        "male": Decimal("5"),
        "female": Decimal("-161"),
        "other": Decimal("-78"),  # (5 + −161) / 2
    }.get(biological_sex, Decimal("-78"))
    return base + sex_const


def compute_nutrition_goal(
    *,
    weight_kg: Decimal,
    height_cm: Decimal,
    age: int,
    biological_sex: str,
    activity_level: str,
    goal_type: str,
    calorie_delta: Decimal | None = None,  # 用户自定义增减; None 用默认
) -> dict[str, Decimal]:
    """完整链路: BMR → TDEE → 目标热量 → 宏量分配。
    返回 daily_calories/protein_g/carbs_g/fat_g。
    """
    bmr = compute_bmr(weight_kg, height_cm, age, biological_sex)

    factor = ACTIVITY_FACTORS.get(activity_level)
    if factor is None:
        raise ValueError(f"未知 activity_level: {activity_level}")
    tdee = bmr * factor

    if goal_type not in GOAL_CALORIE_DELTA:
        raise ValueError(f"未知 goal_type: {goal_type}")
    delta = calorie_delta if calorie_delta is not None else GOAL_CALORIE_DELTA[goal_type]
    target_calories = tdee + delta

    # 宏量: 蛋白先锁(按体重), 脂肪按热量百分比, 碳水填剩余
    protein_g = PROTEIN_G_PER_KG * weight_kg
    fat_g = (target_calories * FAT_PCT_OF_CALORIES) / KCAL_PER_G_FAT
    used = protein_g * KCAL_PER_G_PROTEIN + fat_g * KCAL_PER_G_FAT
    carbs_g = (target_calories - used) / KCAL_PER_G_CARB
    # 碳水兜底: 极端输入(高蛋白+低热量)可能算出负数, 夹到 0
    if carbs_g < 0:
        carbs_g = Decimal("0")

    return {
        "daily_calories": _round1(target_calories),
        "daily_protein_g": _round1(protein_g),
        "daily_carbs_g": _round1(carbs_g),
        "daily_fat_g": _round1(fat_g),
    }