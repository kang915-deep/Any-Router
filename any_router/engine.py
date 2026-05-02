"""意图解析引擎 — 调用 DeepSeek-V4 API 将自然语言解析为结构化 JSON。"""

import json
from typing import Any

import requests

from any_router.config import Settings
from any_router.exceptions import (
    APIConnectionError,
    APIResponseError,
    ParsingError,
)

# 极致精简的 System Prompt (~150 Tokens)
SYSTEM_PROMPT = """你是意图路由器。将用户输入解析为 JSON。
可用操作: accounting(记账)

记账参数 (所有字段均为必填):
  type: 交易类型，必须为 "expense"(支出) 或 "income"(收入)
  amount: 金额，必须为正数(数字)
  category: 分类。优先使用: 餐饮, 交通, 购物, 日用, 娱乐, 医疗, 工资, 其他
  note: 备注(可选，默认为空)
  time: 时间(ISO 8601)。除非用户明确提到“昨天”、“上周五”或具体日期，否则请忽略此字段。

必须返回有效的 JSON 对象，确保包含 "action" 和 "params" 字段。"""


def parse(user_input: str) -> dict[str, Any]:
    """将用户自然语言输入解析为结构化意图 JSON。

    Args:
        user_input: 用户输入的自然语言文本。

    Returns:
        结构化意图字典，包含 action 和 params。

    Raises:
        APIConnectionError: API 连接失败。
        APIResponseError: API 返回异常。
        ParsingError: 响应无法解析为有效 JSON。
    """
    settings = Settings()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]

    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": messages,
        "response_format": {"type": "json_object"},
        # 极低 Token 消耗: 简短输入 + json_object 输出
        "max_tokens": 256,
        "temperature": 0.1,  # 低温度，确保一致性
    }

    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=15,
        )
    except requests.Timeout:
        raise APIConnectionError("请求 DeepSeek API 超时，请检查网络连接。")
    except requests.ConnectionError:
        raise APIConnectionError("无法连接 DeepSeek API，请检查网络连接和 API 地址。")
    except requests.RequestException as e:
        raise APIConnectionError(f"HTTP 请求失败: {e}")

    if resp.status_code != 200:
        raise APIResponseError(
            f"API 返回异常 (HTTP {resp.status_code}): {resp.text[:500]}"
        )

    try:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise APIResponseError(f"API 响应格式异常: {e}\n响应内容: {resp.text[:500]}")

    # 解析 AI 返回的 JSON
    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        raise ParsingError(f"AI 返回内容不是有效 JSON: {e}\n内容: {content[:500]}")

    # 校验必要字段
    if "action" not in result:
        raise ParsingError(f"AI 返回缺少 action 字段: {result}")

    return result
