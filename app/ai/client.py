# app/ai/client.py
"""Anthropic 调用封装 —— 唯一有副作用(调外部 API)的地方。

把"怎么调 API"隔离在此: 换供应商/模型只改这一层, 业务逻辑不动。
测试时 mock generate_recipe_raw, 不真调 API。
"""
from __future__ import annotations

from dataclasses import dataclass

from anthropic import AsyncAnthropic

from app.ai.prompts import SYSTEM_PROMPT
from app.ai.recipe_tool import SAVE_RECIPE_TOOL
from app.core.config import get_settings


@dataclass
class AiResult:
    """AI 调用的结构化结果。tool_input 即 save_recipe 的入参(干净 JSON)。"""
    tool_input: dict
    input_tokens: int
    output_tokens: int


class AiError(Exception):
    """AI 调用/解析失败(超时、拒答、没按工具返回等)。"""


async def generate_recipe_raw(user_message: str) -> AiResult:
    """调 Anthropic 生成菜谱, 强制走 save_recipe 工具, 返回工具入参 + token 数。

    只负责"拿到结构化结果", 不做 id 校验/落库(那是业务层的事)。
    """
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    resp = await client.messages.create(
        model=settings.anthropic_model,
        max_tokens=settings.anthropic_max_tokens,
        system=SYSTEM_PROMPT,
        tools=[SAVE_RECIPE_TOOL],
        # 强制调用 save_recipe, 保证拿到结构化输出而非自然语言
        tool_choice={"type": "tool", "name": "save_recipe"},
        messages=[{"role": "user", "content": user_message}],
    )

    # 从返回内容里取出 tool_use 块(强制 tool_choice 下应有且仅有一个)
    tool_input = None
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "save_recipe":
            tool_input = block.input
            break
    if tool_input is None:
        raise AiError("模型未按 save_recipe 工具返回结果")

    return AiResult(
        tool_input=tool_input,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
    )