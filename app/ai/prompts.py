# app/ai/prompts.py
"""Prompt 构造 —— 纯函数, 不调 API, 好测。"""
from __future__ import annotations

SYSTEM_PROMPT = (
    "你是一个营养菜谱生成助手。根据用户需求生成一个可行的菜谱。\n"
    "严格约束:\n"
    "1. 只能使用【可用食材】清单里的食材, 用其 ingredient_id 引用, "
    "绝不使用清单外的食材。\n"
    "2. 用量填克数(amount_grams)。\n"
    "3. 必须调用 save_recipe 工具返回结果, 不要用自然语言回复。"
)


def build_ingredient_catalog(ingredients: list[dict]) -> str:
    """把可用食材清单(grounding 数据)拼成紧凑文本。
    每项只给 id + 名字(+分类), 不给营养详情 —— 省 input token。
    ingredients: [{"id": int, "name": str, "category": str | None}, ...]
    """
    lines = []
    for ing in ingredients:
        cat = f" ({ing['category']})" if ing.get("category") else ""
        lines.append(f"- id={ing['id']}: {ing['name']}{cat}")
    return "\n".join(lines)


def build_user_message(
    ingredients: list[dict],
    *,
    free_text: str | None = None,
    cuisine: str | None = None,
    goal: str | None = None,
    servings: int | None = None,
) -> str:
    """拼用户侧 prompt: 可用食材(grounding) + 结构化选项 + 一句自由文本。"""
    parts = ["【可用食材】(只能用这些, 用 id 引用):", build_ingredient_catalog(ingredients)]

    constraints = []
    if cuisine:
        constraints.append(f"菜系: {cuisine}")
    if goal:
        constraints.append(f"目标: {goal}")
    if servings:
        constraints.append(f"份数: {servings}")
    if constraints:
        parts.append("\n【要求】: " + "; ".join(constraints))
    if free_text:
        parts.append(f"\n【补充说明】: {free_text}")

    parts.append("\n请调用 save_recipe 工具生成一个菜谱。")
    return "\n".join(parts)

MEAL_PLAN_SYSTEM_PROMPT = (
    "你是一个周计划编排助手。根据用户的天数和餐段, 从【可用做法清单】里挑选,"
    "排出一份多样、不过度重复的计划。\n"
    "严格约束:\n"
    "1. 每一餐只能用清单里的 recipe_variant_id, 绝不使用清单外的。\n"
    "2. day_offset 从 0 到 (天数-1); meal_type 只能用请求里给的餐段。\n"
    "3. 尽量不要连续多天重复同一做法。\n"
    "4. 必须调用 save_meal_plan 工具返回, 不要用自然语言回复。"
)


def build_variant_catalog(variants: list[dict]) -> str:
    """可用做法清单(grounding): 每项 variant_id + 菜谱名 + 做法名(+主料)。"""
    lines = []
    for v in variants:
        ings = f" [{', '.join(v['ingredients'])}]" if v.get("ingredients") else ""
        lines.append(
            f"- variant_id={v['variant_id']}: {v['recipe_name']}"
            f"（{v['variant_name']}）{ings}"
        )
    return "\n".join(lines)


def build_meal_plan_message(
    variants: list[dict], *, days: int, meals: list[str],
    free_text: str | None = None,
) -> str:
    """拼周计划 prompt: 可用做法(grounding) + 天数 + 餐段 + 一句自由文本。"""
    parts = [
        "【可用做法】(只能用这些, 用 variant_id 引用):",
        build_variant_catalog(variants),
        f"\n【要求】: 天数 {days}（day_offset 0..{days - 1}）; "
        f"每天餐段: {', '.join(meals)}",
    ]
    if free_text:
        parts.append(f"\n【补充说明】: {free_text}")
    parts.append("\n请调用 save_meal_plan 工具生成计划。")
    return "\n".join(parts)