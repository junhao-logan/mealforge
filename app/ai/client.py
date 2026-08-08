# app/ai/client.py
"""LLM 调用封装(adapter 层)—— 唯一绑定具体供应商的地方, 当前: Google Gemini。

换供应商只改本文件: 保持 generate_*_raw 的输入(prompt)和输出
(AiResult: tool_input + token 数)不变, services/端点/测试全部无感。
测试时 mock generate_*_raw, 不真调 API。
"""
from __future__ import annotations

from dataclasses import dataclass

from google import genai
from google.genai import types

from app.ai.meal_plan_tool import SAVE_MEAL_PLAN_TOOL
from app.ai.prompts import MEAL_PLAN_SYSTEM_PROMPT, SYSTEM_PROMPT
from app.ai.recipe_tool import SAVE_RECIPE_TOOL
from app.core.config import get_settings


@dataclass
class AiResult:
    """AI 调用的结构化结果(供应商无关)。tool_input 即工具函数的入参。"""
    tool_input: dict
    input_tokens: int
    output_tokens: int


class AiError(Exception):
    """AI 调用/解析失败(超时、拒答、没按工具返回等)。"""


async def _call_tool(system_prompt: str, user_message: str, tool_def: dict) -> AiResult:
    """通用: 强制 Gemini 调用指定 function 并返回其入参 + token。

    recipe 生成、meal_plan 生成共用此核 —— 供应商细节只此一处, 加新 AI 功能
    只需新增 tool schema + 一个瘦包装, 不重复调用逻辑。
    """
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)

    fn = types.FunctionDeclaration(
        name=tool_def["name"],
        description=tool_def["description"],
        parameters_json_schema=tool_def["input_schema"],
    )
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=settings.ai_max_tokens,
        tools=[types.Tool(function_declarations=[fn])],
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="ANY")
        ),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    try:
        resp = await client.aio.models.generate_content(
            model=settings.gemini_model, contents=user_message, config=config,
        )
    except Exception as e:   # 网络/超时/SDK 错误, 统一成 AiError
        raise AiError(f"Gemini 调用失败: {e}") from e

    calls = resp.function_calls
    if not calls:
        raise AiError(f"模型未按 {tool_def['name']} 函数返回结果")
    call = calls[0]
    if call.name != tool_def["name"]:
        raise AiError(f"模型调用了非预期函数: {call.name}")

    usage = resp.usage_metadata
    return AiResult(
        tool_input=dict(call.args) if call.args else {},
        input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
        output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
    )


async def generate_recipe_raw(user_message: str) -> AiResult:
    """生成单个菜谱(Week 7)。"""
    return await _call_tool(SYSTEM_PROMPT, user_message, SAVE_RECIPE_TOOL)


async def generate_meal_plan_raw(user_message: str) -> AiResult:
    """生成周计划(Week 8)。"""
    return await _call_tool(MEAL_PLAN_SYSTEM_PROMPT, user_message, SAVE_MEAL_PLAN_TOOL)