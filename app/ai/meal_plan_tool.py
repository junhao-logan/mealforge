# app/ai/meal_plan_tool.py
"""save_meal_plan 工具 schema —— AI 必须按此结构返回周计划(结构化输出)。

grounding 关键: entries[].recipe_variant_id 只能取 prompt 里给的可用做法清单中的 id。
day_offset: 相对 start_date 的偏移(0=第一天)。meal_type: 请求指定的餐段。

阶段B(recipe_source='new'): 每条 entry 二选一 —— 用已有做法(recipe_variant_id),
或现编新菜谱(new_recipe)。new_recipe 的配料要么引用可用食材 id, 要么给 new_name 新建。
"""

SAVE_MEAL_PLAN_TOOL = {
    "name": "save_meal_plan",
    "description": (
        "保存生成的周计划。每一餐二选一: 用【可用做法清单】里的 recipe_variant_id, "
        "或现编一个 new_recipe。new_recipe 的配料优先引用【可用食材清单】里的 ingredient_id "
        "(数量用该食材的单位, 可小数如 0.8); 清单里没有的食材才用 new_name 新建并给 per100g 估算。"
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
                            "description": "已有做法的 id(与 new_recipe 二选一)",
                        },
                        "servings": {
                            "type": "number",
                            "description": "这一餐吃几份, 默认 1",
                        },
                        "new_recipe": {
                            "type": "object",
                            "description": "现编新菜谱(与 recipe_variant_id 二选一)",
                            "properties": {
                                "name": {"type": "string"},
                                "cuisine": {"type": "string"},
                                "instructions": {
                                    "type": "string",
                                    "description": "分步做法, 纯文本(换行分步)",
                                },
                                "ingredients": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "ingredient_id": {
                                                "type": "integer",
                                                "description": "引用可用食材清单里的 id(优先)",
                                            },
                                            "new_name": {
                                                "type": "string",
                                                "description": "清单没有才用: 新食材名(按语言)",
                                            },
                                            "amount": {
                                                "type": "number",
                                                "description": "用量: 已有食材按其单位; 新食材按克",
                                            },
                                            "per100g": {
                                                "type": "object",
                                                "description": "仅新食材: 每 100g 营养估算",
                                                "properties": {
                                                    "calories": {"type": "number"},
                                                    "protein": {"type": "number"},
                                                    "carbs": {"type": "number"},
                                                    "fat": {"type": "number"},
                                                },
                                            },
                                        },
                                        "required": ["amount"],
                                    },
                                    "minItems": 1,
                                },
                            },
                            "required": ["name", "instructions", "ingredients"],
                        },
                    },
                    "required": ["day_offset", "meal_type"],
                },
                "minItems": 1,
            },
        },
        "required": ["entries"],
    },
}
