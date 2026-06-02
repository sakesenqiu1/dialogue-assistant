from typing import Any

from app.ai_client import chat_json, format_messages_for_ai
from app.message_sampling import ORDER_NOTE
from app.profile_ai import build_prompt_context

# 发送辅助时从全部材料中均匀节选的条数（非“最后 N 条”）
CONTEXT_SAMPLE_SIZE = 80

ANALYZE_SYSTEM = """你是擅长与双相（躁郁）患者亲友沟通的顾问。
用户已建立针对 Ta 的个性化沟通画像（综合全部历史材料提炼，非仅最近几条）。
""" + ORDER_NOTE + """

任务：
1. 以画像为主、节选材料为辅，评估草稿激怒对方的可能性（0-100）。
2. 明确指出与画像中哪些触发点/模式相关（personalized_reasons）。
3. 根据用户「真实意图」，给出 2-3 条贴合 Ta 特点的优化文案。
4. 给出可操作的发送前建议（advice）。
勿因节选材料中靠后的条目而高估风险或改变判断。

原则：不诊断、不说教；中文；务实有同理心。

只输出合法 JSON：
{
  "anger_risk": 0,
  "anger_level": "低|中|高",
  "anger_reasons": ["一般原因"],
  "personalized_reasons": ["结合 Ta 个人画像的原因"],
  "optimized_versions": [
    {"label": "温和版", "text": "..."},
    {"label": "贴合 Ta 习惯版", "text": "..."}
  ],
  "advice": "发送前建议",
  "profile_tip": "一句基于画像的提醒（可选）"
}"""


async def analyze_message(
    draft: str,
    intent: str | None,
    context_messages: list[dict[str, str]],
    profile: dict[str, Any] | None = None,
    user_narrative: str | None = None,
) -> tuple[dict[str, Any], str]:
    profile_block = build_prompt_context(profile, user_narrative)
    if context_messages:
        context_text = format_messages_for_ai(
            context_messages, limit=CONTEXT_SAMPLE_SIZE
        )
    else:
        context_text = ""

    user_parts = []
    if profile_block:
        user_parts.append(profile_block)
    if context_text:
        user_parts.append(f"【参考材料节选】\n{context_text}")
    if intent:
        user_parts.append(f"【我想表达的真实意思】\n{intent}")
    user_parts.append(f"【准备发送的草稿】\n{draft}")
    user_parts.append("请以画像为主、综合全部历史模式分析激怒风险并优化文案。")

    parsed, raw = await chat_json(
        ANALYZE_SYSTEM,
        "\n\n".join(user_parts),
        temperature=0.4,
    )

    anger_risk = max(0, min(100, int(parsed.get("anger_risk", 50))))

    optimized = parsed.get("optimized_versions", [])
    normalized = []
    if isinstance(optimized, list):
        for i, item in enumerate(optimized):
            if isinstance(item, dict):
                normalized.append(
                    {
                        "label": item.get("label", f"方案{i + 1}"),
                        "text": item.get("text", ""),
                    }
                )
            elif isinstance(item, str):
                normalized.append({"label": f"方案{i + 1}", "text": item})

    anger_reasons = parsed.get("anger_reasons", [])
    if not isinstance(anger_reasons, list):
        anger_reasons = [str(anger_reasons)]

    personalized = parsed.get("personalized_reasons", [])
    if not isinstance(personalized, list):
        personalized = [str(personalized)] if personalized else []

    result = {
        "anger_risk": anger_risk,
        "anger_level": str(parsed.get("anger_level", "中")),
        "anger_reasons": anger_reasons,
        "personalized_reasons": personalized,
        "optimized_versions": normalized,
        "advice": str(parsed.get("advice", "")),
        "profile_tip": str(parsed.get("profile_tip", "")),
    }
    return result, raw
