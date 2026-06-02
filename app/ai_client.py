import json
import re
from typing import Any

import httpx

from app.config import settings
from app.message_sampling import ORDER_NOTE, sample_for_context


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
        raise


async def chat_json(
    system: str, user: str, temperature: float = 0.35
) -> tuple[dict[str, Any], str]:
    if not settings.deepseek_api_key:
        raise ValueError("未配置 DEEPSEEK_API_KEY，请在 .env 文件中填写")

    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    url = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    raw = data["choices"][0]["message"]["content"]
    return extract_json(raw), raw


def format_messages_for_ai(
    messages: list[dict[str, str]],
    limit: int | None = None,
    *,
    even_if_no_limit: bool = False,
) -> str:
    """
    将对话与 Ta 自述格式化供模型阅读。
    limit 时使用均匀抽样（非取最后 N 条）。
    """
    if limit is not None:
        subset = sample_for_context(messages, limit)
        header = (
            f"{ORDER_NOTE}\n"
            f"（以下从全部 {len(messages)} 条中均匀节选 {len(subset)} 条供参考）\n"
        )
    else:
        subset = messages
        header = f"{ORDER_NOTE}\n（共 {len(messages)} 条，请综合全部）\n"

    chat_lines: list[str] = []
    self_parts: list[str] = []

    for idx, m in enumerate(subset, 1):
        role = m.get("role", "friend")
        content = m.get("content", "").strip()
        if not content:
            continue
        if role == "me":
            chat_lines.append(f"[{idx}] 我: {content}")
        elif role == "self_narrative":
            self_parts.append(f"[{idx}] {content}")
        else:
            chat_lines.append(f"[{idx}] Ta: {content}")

    blocks: list[str] = [header]
    if chat_lines:
        blocks.append("【双方对话】\n" + "\n".join(chat_lines))
    if self_parts:
        joined = "\n\n---\n\n".join(self_parts)
        blocks.append(
            "【Ta 自述（第一人称陈述，非对话轮次，权重与对话同等）】\n" + joined
        )
    return "\n\n".join(blocks)
