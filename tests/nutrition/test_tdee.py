# tests/nutrition/test_tdee.py
"""TDEE / BMR / 宏量分配的公式正确性(N1)。纯函数, 不需 DB。"""
from decimal import Decimal

import pytest

from app.nutrition.services import (
    compute_bmr,
    compute_nutrition_goal,
)

# ---- BMR (Mifflin-St Jeor) ----

def test_bmr_male():
    """男: 10W + 6.25H − 5A + 5。70kg/175cm/30岁 = 1648.75。"""
    bmr = compute_bmr(Decimal("70"), Decimal("175"), 30, "male")
    # 10*70 + 6.25*175 - 5*30 + 5 = 700 + 1093.75 - 150 + 5
    assert bmr == Decimal("1648.75")


def test_bmr_female():
    """女: 常数 −161。同参数 = 1482.75。"""
    bmr = compute_bmr(Decimal("70"), Decimal("175"), 30, "female")
    assert bmr == Decimal("1482.75")


def test_bmr_other_is_midpoint():
    """other: 常数取男女均值 −78。"""
    bmr = compute_bmr(Decimal("70"), Decimal("175"), 30, "other")
    assert bmr == Decimal("1565.75")   # base(1643.75) + (-78)


def test_bmr_unknown_sex_defaults_other():
    """未知 sex 落到 other(−78), 不崩。"""
    bmr = compute_bmr(Decimal("70"), Decimal("175"), 30, "???")
    assert bmr == Decimal("1565.75")


# ---- TDEE + 目标 + 宏量 ----

def test_tdee_applies_activity_factor():
    """TDEE = BMR × 活动系数。maintenance(delta 0) 时 daily=TDEE。"""
    r = compute_nutrition_goal(
        weight_kg=Decimal("70"), height_cm=Decimal("175"), age=30,
        biological_sex="male", activity_level="sedentary",
        goal_type="maintenance",
    )
    # BMR 1648.75 × 1.2 = 1978.5, delta 0
    assert r["daily_calories"] == Decimal("1978.5")


def test_fat_loss_subtracts_default_delta():
    """fat_loss 默认 −500。"""
    r = compute_nutrition_goal(
        weight_kg=Decimal("70"), height_cm=Decimal("175"), age=30,
        biological_sex="male", activity_level="sedentary",
        goal_type="fat_loss",
    )
    assert r["daily_calories"] == Decimal("1478.5")   # 1978.5 - 500


def test_custom_delta_overrides_default():
    """用户自定义 calorie_delta 覆盖 goal 默认。"""
    r = compute_nutrition_goal(
        weight_kg=Decimal("70"), height_cm=Decimal("175"), age=30,
        biological_sex="male", activity_level="sedentary",
        goal_type="fat_loss", calorie_delta=Decimal("-300"),
    )
    assert r["daily_calories"] == Decimal("1678.5")   # 用 -300 不是 -500


def test_protein_scales_with_weight():
    """蛋白 = 2g/kg 体重。70kg → 140g。"""
    r = compute_nutrition_goal(
        weight_kg=Decimal("70"), height_cm=Decimal("175"), age=30,
        biological_sex="male", activity_level="moderate",
        goal_type="maintenance",
    )
    assert r["daily_protein_g"] == Decimal("140.0")


def test_unknown_activity_raises():
    """未知活动等级 → ValueError。"""
    with pytest.raises(ValueError, match="activity_level"):
        compute_nutrition_goal(
            weight_kg=Decimal("70"), height_cm=Decimal("175"), age=30,
            biological_sex="male", activity_level="bogus",
            goal_type="maintenance",
        )


def test_unknown_goal_raises():
    """未知目标 → ValueError。"""
    with pytest.raises(ValueError, match="goal_type"):
        compute_nutrition_goal(
            weight_kg=Decimal("70"), height_cm=Decimal("175"), age=30,
            biological_sex="male", activity_level="moderate",
            goal_type="bogus",
        )


def test_carbs_clamped_to_zero_on_extreme():
    """极端输入(高蛋白占满热量)碳水算出负 → 夹到 0, 不返回负数。"""
    r = compute_nutrition_goal(
        weight_kg=Decimal("200"), height_cm=Decimal("150"), age=80,
        biological_sex="female", activity_level="sedentary",
        goal_type="fat_loss",
    )
    assert r["daily_carbs_g"] >= Decimal("0")   # 不为负