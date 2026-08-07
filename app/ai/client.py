# app/ai/client.py
"""LLM 调用封装(adapter 层)—— 唯一绑定具体供应商的地方, 当前: Google Gemini。

换供应商只改本文件: 保持 generate_recipe_raw 的输入(prompt)和输出
(AiResult: tool_input + token 数)不变, services/端点/测试全部无感。
测试时 mock generate_recipe_raw, 不真调 API。
"""
from __future__ import annotations

from dataclasses import dataclass

from google import genai
from google.genai import types

from app.ai.prompts import SYSTEM_PROMPT
from app.ai.recipe_tool import SAVE_RECIPE_TOOL
from app.core.config import get_settings


@dataclass
class AiResult:
    """AI 调用的结构化结果(供应商无关)。tool_input 即 save_recipe 的入参。"""
    tool_input: dict
    input_tokens: int
    output_tokens: int


class AiError(Exception):
    """AI 调用/解析失败(超时、拒答、没按工具返回等)。"""


def _build_tool() -> types.Tool:
    """把中立的 save_recipe JSON schema 包成 Gemini function declaration。"""
    fn = types.FunctionDeclaration(
        name=SAVE_RECIPE_TOOL["name"],
        description=SAVE_RECIPE_TOOL["description"],
        parameters_json_schema=SAVE_RECIPE_TOOL["input_schema"],
    )
    return types.Tool(function_declarations=[fn])


async def generate_recipe_raw(user_message: str) -> AiResult:
    """调 Gemini 生成菜谱, 强制走 save_recipe 函数, 返回函数入参 + token 数。

    只负责"拿到结构化结果", 不做 id 校验/落库(那是业务层的事)。
    """
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        max_output_tokens=settings.ai_max_tokens,
        tools=[_build_tool()],
        # mode=ANY: 强制调用函数(而非自然语言回复), 拿到结构化输出
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="ANY")
        ),
        # 关掉自动函数执行: 我们要自己拿到函数调用参数, 不让 SDK 代执行
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    try:
        resp = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=user_message,
            config=config,
        )
    except Exception as e:   # 网络/超时/SDK 错误, 统一成 AiError
        raise AiError(f"Gemini 调用失败: {e}") from e

    calls = resp.function_calls
    if not calls:
        raise AiError("模型未按 save_recipe 函数返回结果")
    call = calls[0]
    if call.name != "save_recipe":
        raise AiError(f"模型调用了非预期函数: {call.name}")

    usage = resp.usage_metadata
    return AiResult(
        tool_input=dict(call.args) if call.args else {},
        input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
        output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
    )