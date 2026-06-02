import json
from typing import Any

from app.ai_client import chat_json, format_messages_for_ai
from app.message_sampling import ORDER_NOTE, CHUNK_SIZE, partition_for_profile

PROFILE_SYSTEM = """你是擅长双相（躁郁）亲友沟通的对话分析专家。
根据用户提供的材料（聊天记录、Ta 自述等）提炼「针对 Ta（对方）」的个性化沟通画像。

""" + ORDER_NOTE + """

要求：
1. 综合全部材料得出结论，各条记录权重相当；排在列表后面不代表更近、更重要。
2. 基于证据：每条结论尽量对应多处材料中的模式，不要空泛套话。
3. 不诊断疾病，不替代医生；只谈沟通与情绪互动。
4. 重点：Ta 的情绪表达、触发点、对你话语的敏感点、有效安抚方式、冲突升级方式、你常踩雷的表达。
5. 输出简体中文；全文用 Ta/对方，不要用她/他。

只输出合法 JSON：
{
  "friend_summary": "Ta 是怎样的人、在材料中呈现的情绪特点（3-5句）",
  "communication_style": "Ta 如何表达不满、开心、求助、冷战等",
  "triggers": ["具体触发点1", "触发点2"],
  "what_works": ["对你有效的话术或做法"],
  "my_blind_spots": ["你容易踩雷的表达习惯"],
  "conflict_patterns": "冲突通常如何开始、升级、缓和",
  "phase_signals": {
    "可能低落时": "材料中的信号",
    "可能躁/激动时": "材料中的信号"
  },
  "do_list": ["建议做的3-6条"],
  "dont_list": ["建议避免的3-6条"],
  "reference_card": "200字以内随身参考：发消息前快速扫一眼的核心要点"
}"""

MERGE_SYSTEM = """你将收到多段针对同一位 Ta 的「部分沟通画像」JSON。
这些片段来自同一份材料的均匀分块，片段之间无时间先后关系，权重完全相等。
请合并为一份完整、去重、可操作的最终画像；勿偏重某一两个片段里的偶然表述。
只输出合法 JSON，字段同上。"""

CHUNK_SYSTEM = """分析以下材料片段，提炼局部沟通画像（结构同完整画像）。
""" + ORDER_NOTE + """
本片段仅为全文之一块，请归纳片段内反复出现的模式，避免把单条特例当成定论。
只输出合法 JSON，字段：
friend_summary, communication_style, triggers, what_works, my_blind_spots,
conflict_patterns, phase_signals, do_list, dont_list, reference_card"""


def format_narrative_block(user_narrative: str | None) -> str:
    text = (user_narrative or "").strip()
    if not text:
        return ""
    return (
        "【用户手动旁白（聊天记录无法体现，分析时必须纳入）】\n" + text
    )


def build_prompt_context(
    profile: dict[str, Any] | None,
    user_narrative: str | None = None,
) -> str:
    parts = []
    narrative = format_narrative_block(user_narrative)
    if narrative:
        parts.append(narrative)
    if not profile:
        return "\n\n".join(parts)
    card = profile.get("reference_card") or profile.get("summary_compact", "")
    triggers = profile.get("triggers", [])
    dont = profile.get("dont_list", [])
    works = profile.get("what_works", [])
    blind = profile.get("my_blind_spots", [])
    parts.append("【已建立的个性化沟通画像（基于全部材料提炼，请优先依据）】")
    if card:
        parts.append(card)
    if triggers:
        parts.append("敏感触发：" + "；".join(triggers[:8]))
    if dont:
        parts.append("避免：" + "；".join(dont[:6]))
    if works:
        parts.append("有效做法：" + "；".join(works[:6]))
    if blind:
        parts.append("我易踩雷：" + "；".join(blind[:5]))
    return "\n\n".join(parts)


def compact_profile_for_storage(full: dict[str, Any]) -> str:
    bits = [
        full.get("reference_card", ""),
        "触发:" + "、".join((full.get("triggers") or [])[:6]),
        "避免:" + "、".join((full.get("dont_list") or [])[:5]),
    ]
    return "\n".join(b for b in bits if b)[:2500]


async def _merge_narrative_into_profile(
    profile: dict[str, Any], user_narrative: str | None
) -> dict[str, Any]:
    narrative = format_narrative_block(user_narrative)
    if not narrative:
        return profile
    user = (
        narrative
        + "\n\n【已有画像 JSON】\n"
        + json.dumps(profile, ensure_ascii=False)
        + "\n\n请将旁白中的信息合并进画像，输出完整 JSON。"
    )
    data, _ = await chat_json(MERGE_SYSTEM, user, temperature=0.25)
    return normalize_profile(data)


async def analyze_chunk(
    messages: list[dict[str, str]],
    chunk_index: int,
    chunk_total: int,
    user_narrative: str | None = None,
) -> dict[str, Any]:
    text = format_messages_for_ai(messages, limit=None)
    user_parts = [
        f"【材料片段 {chunk_index}/{chunk_total}，共 {len(messages)} 条】\n{text}",
    ]
    narrative = format_narrative_block(user_narrative)
    if narrative:
        user_parts.append(narrative)
    data, _ = await chat_json(CHUNK_SYSTEM, "\n\n".join(user_parts), temperature=0.3)
    return data


async def merge_profiles(partials: list[dict[str, Any]]) -> dict[str, Any]:
    blob = json.dumps(partials, ensure_ascii=False, indent=0)
    user = f"【共 {len(partials)} 个等权片段画像，请综合合并】\n{blob}"
    data, _ = await chat_json(MERGE_SYSTEM, user, temperature=0.25)
    return normalize_profile(data)


def normalize_profile(data: dict[str, Any]) -> dict[str, Any]:
    for key in ("triggers", "what_works", "my_blind_spots", "do_list", "dont_list"):
        val = data.get(key, [])
        if not isinstance(val, list):
            data[key] = [str(val)] if val else []
    if not isinstance(data.get("phase_signals"), dict):
        data["phase_signals"] = {}
    for field in (
        "friend_summary",
        "communication_style",
        "conflict_patterns",
        "reference_card",
    ):
        data.setdefault(field, "")
    data["summary_compact"] = compact_profile_for_storage(data)
    return data


NARRATIVE_ONLY_SYSTEM = """你是擅长双相（躁郁）亲友沟通的对话分析专家。
用户提供了关于 Ta 的手动旁白。请仅根据旁白提炼画像；未提及的不要编造。
全文用 Ta/对方。只输出合法 JSON，字段同完整画像。"""


async def build_personal_profile(
    messages: list[dict[str, str]],
    user_narrative: str | None = None,
) -> tuple[dict[str, Any], str]:
    n = len(messages)
    narrative = format_narrative_block(user_narrative)

    if n == 0 and not narrative:
        raise ValueError("请先导入聊天记录，或填写手动旁白后再生成画像")

    if n == 0 and narrative:
        user = narrative + "\n\n请根据旁白提炼 Ta 的沟通画像。"
        data, raw = await chat_json(NARRATIVE_ONLY_SYSTEM, user, temperature=0.35)
        return normalize_profile(data), raw

    if n <= CHUNK_SIZE:
        text = format_messages_for_ai(messages, limit=None)
        user_parts = [f"【全部材料，共 {n} 条】\n{text}"]
        if narrative:
            user_parts.append(narrative)
        user_parts.append("请综合全部条目提炼画像；旁白须写入相应字段。")
        data, raw = await chat_json(
            PROFILE_SYSTEM, "\n\n".join(user_parts), temperature=0.35
        )
        return normalize_profile(data), raw

    chunks = partition_for_profile(messages)
    partials: list[dict[str, Any]] = []
    total = len(chunks)
    for idx, chunk in enumerate(chunks):
        partial = await analyze_chunk(
            chunk,
            idx + 1,
            total,
            user_narrative if idx == 0 else None,
        )
        partial["_chunk"] = f"{idx + 1}/{total}"
        partials.append(partial)

    if len(partials) == 1:
        merged_one = normalize_profile(partials[0])
        if narrative:
            merged_one = await _merge_narrative_into_profile(merged_one, user_narrative)
        return merged_one, json.dumps(partials[0], ensure_ascii=False)

    merged = await merge_profiles(partials)
    if narrative:
        merged = await _merge_narrative_into_profile(merged, user_narrative)
    raw = json.dumps({"partials": len(partials), "merged": merged}, ensure_ascii=False)
    return merged, raw
