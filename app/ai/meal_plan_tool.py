# app/ai/meal_plan_tool.py
"""save_meal_plan 工具 schema —— AI 必须按此结构返回周计划(结构化输出)。

grounding 关键: entries[].recipe_variant_id 只能取 prompt 里给的可用做法清单中的 id。
day_offset: 相对 start_date 的偏移(0=第一天)。meal_type: 请求指定的餐段。
"""

SAVE_MEAL_PLAN_TOOL = {
    "name": "save_meal_plan",
    "description": (
        "保存生成的周计划。每一餐必须从用户提供的【可用做法清单】中选择, "
        "用其 recipe_variant_id 引用; 不得使用清单外的做法。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "entries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "day_offset": {
                            "type": "integer",
                            "description": "相对起始日的天偏移, 0 为第一天",
                            "minimum": 0,
                        },
                        "meal_type": {
                            "type": "string",
                            "description": "餐段, 只能用请求里给的(如 lunch/dinner)",
                        },
                        "recipe_variant_id": {
                            "type": "integer",
                            "description": "必须是可用做法清单中的 id",
                        },
                        "servings": {
                            "type": "number",
                            "description": "这一餐吃几份, 默认 1",
                        },
                    },
                    "required": ["day_offset", "meal_type", "recipe_variant_id"],
                },
                "minItems": 1,
            },
        },
        "required": ["entries"],
    },
}