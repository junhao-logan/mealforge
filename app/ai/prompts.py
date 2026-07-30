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