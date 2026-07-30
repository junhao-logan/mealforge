# app/ai/recipe_tool.py
"""save_recipe 工具 schema —— AI 必须按此结构返回菜谱(结构化输出)。

grounding 关键: ingredients[].ingredient_id 只能取 prompt 里给的清单中的 id,
AI 不能自造食材, 从根上杜绝幻觉出不存在的食材。
"""

SAVE_RECIPE_TOOL = {
    "name": "save_recipe",
    "description": (
        "保存生成的菜谱。所有食材必须从用户提供的可用食材清单中选择, "
        "用其 ingredient_id 引用; 不得使用清单外的食材。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "菜谱名称"},
            "description": {"type": "string", "description": "一句话简介"},
            "cuisine": {
                "type": "string",
                "description": "菜系, 如 chinese/western/japanese",
            },
            "cooking_time_minutes": {"type": "integer"},
            "difficulty": {
                "type": "string",
                "enum": ["easy", "medium", "hard"],
            },
            "servings": {"type": "integer", "minimum": 1},
            "instructions": {
                "type": "string",
                "description": "分步做法, 纯文本(可用换行分步)",
            },
            "ingredients": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ingredient_id": {
                            "type": "integer",
                            "description": "必须是可用食材清单中的 id",
                        },
                        "amount_grams": {
                            "type": "number",
                            "description": "用量(克)",
                        },
                    },
                    "required": ["ingredient_id", "amount_grams"],
                },
                "minItems": 1,
            },
        },
        "required": ["name", "servings", "instructions", "ingredients"],
    },
}