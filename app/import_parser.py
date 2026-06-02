"""Parse pasted or exported chat logs into role-tagged messages."""
import re
from typing import Literal

Role = Literal["me", "friend", "self_narrative"]

# 自述行：Ta 的第一人称陈述（非对话轮次）
NARRATIVE_PREFIX = re.compile(
    r"^\s*"
    r"(?P<role>自述|Ta自述|TA自述|对方自述|自我陈述|日记|随笔)"
    r"\s*[：:]\s*"
    r"(?P<content>.+)$",
    re.IGNORECASE,
)

# 行首角色标记：我 / 朋友 / Ta 等
LINE_PREFIX = re.compile(
    r"^\s*"
    r"(?P<role>我|本人|自己|男方|女方|男朋友|女朋友|老公|老婆|"
    r"朋友|Ta|TA|ta|对方|她|他|女友|男友)"
    r"\s*[：:]\s*"
    r"(?P<content>.+)$",
    re.IGNORECASE,
)

BLOCK_SPLIT = re.compile(r"\n\s*---\s*\n|\n\s*\n\s*\n+")


def _nick_line(nick: str) -> re.Pattern:
    esc = re.escape(nick.strip())
    return re.compile(
        rf"^\s*(?:{esc})\s*[：:]\s*(?P<content>.+)$",
        re.IGNORECASE,
    )


TIMESTAMP_ROLE = re.compile(
    r"^\s*\[?[\d\-/年月日\s:.]{8,30}\]?\s*"
    r"(?P<role>我|朋友|Ta|TA|对方|她|他|自述)\s*[：:]\s*(?P<content>.+)$"
)


def _map_role(token: str) -> Role:
    t = token.strip()
    if t in ("我", "本人", "自己", "男方", "女方", "男朋友", "女朋友", "老公", "老婆"):
        return "me"
    if t in ("自述", "Ta自述", "TA自述", "对方自述", "自我陈述", "日记", "随笔"):
        return "self_narrative"
    return "friend"


def parse_self_narrative_text(text: str) -> list[dict[str, str]]:
    """
    批量导入 Ta 自述：支持
    - 自述：开头每段
    - 空行或 --- 分隔的多段正文（无角色前缀时整段视为自述）
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []

    messages: list[dict[str, str]] = []
    lines = text.split("\n")
    pending: list[str] = []
    pending_is_prefixed = False

    def flush_prefixed():
        nonlocal pending, pending_is_prefixed
        if pending:
            content = "\n".join(pending).strip()
            if content:
                messages.append({"role": "self_narrative", "content": content})
        pending = []
        pending_is_prefixed = False

    for raw in lines:
        line = raw.strip()
        if not line:
            if pending_is_prefixed and pending:
                pending.append("")
            continue

        m = NARRATIVE_PREFIX.match(line)
        if m:
            flush_prefixed()
            pending_is_prefixed = True
            first = m.group("content").strip()
            pending = [first] if first else []
        elif pending_is_prefixed:
            pending.append(line)
        else:
            flush_prefixed()

    flush_prefixed()

    if messages:
        return messages

    # 无「自述：」前缀 → 按空行/--- 分块
    blocks = [b.strip() for b in BLOCK_SPLIT.split(text) if b.strip()]
    if not blocks:
        blocks = [text]
    return [{"role": "self_narrative", "content": b} for b in blocks if b]


def parse_chat_text(
    text: str,
    friend_nickname: str | None = None,
) -> list[dict[str, str]]:
    """Return list of {role, content} from raw paste (含对话与混排的自述行)."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    nick_re = _nick_line(friend_nickname) if friend_nickname else None

    messages: list[dict[str, str]] = []
    pending_role: Role | None = None
    buffer: list[str] = []

    def flush():
        nonlocal buffer, pending_role
        if pending_role and buffer:
            content = "\n".join(buffer).strip()
            if content:
                messages.append({"role": pending_role, "content": content})
        buffer = []
        pending_role = None

    for raw in lines:
        line = raw.strip()
        if not line:
            if buffer:
                buffer.append("")
            continue

        matched = None
        m_narr = NARRATIVE_PREFIX.match(line)
        if m_narr:
            matched = ("self_narrative", m_narr.group("content").strip())
        else:
            for pat in (LINE_PREFIX, TIMESTAMP_ROLE):
                m = pat.match(line)
                if m:
                    matched = (_map_role(m.group("role")), m.group("content").strip())
                    break

        if not matched and nick_re:
            m = nick_re.match(line)
            if m:
                matched = ("friend", m.group("content").strip())

        if not matched:
            m2 = re.match(r"^我\s+(.+)$", line)
            if m2:
                matched = ("me", m2.group(1).strip())

        if matched:
            flush()
            pending_role, first = matched
            buffer = [first] if first else []
        elif pending_role:
            buffer.append(line)

    flush()
    return messages
