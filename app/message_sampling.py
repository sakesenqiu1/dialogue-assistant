"""Sample and partition messages without assuming chronological order."""

from __future__ import annotations

ORDER_NOTE = (
    "【重要】以下材料按导入/查阅顺序排列，不代表时间先后；"
    "分析时须综合全部条目、等权看待，勿因排在末尾而提高权重。"
)

CHUNK_SIZE = 80
# 最多分块数；超出时在全库上均匀抽样后再分块，避免只分析头尾
MAX_CHUNKS = 16


def even_sample(messages: list, cap: int) -> list:
    """在整条序列上均匀取样，避免只取开头或结尾。"""
    n = len(messages)
    if n <= cap:
        return messages
    if cap <= 1:
        return messages[:1]
    step = (n - 1) / (cap - 1)
    indices = sorted({int(round(i * step)) for i in range(cap)})
    while len(indices) < cap and len(indices) < n:
        for i in range(n):
            if i not in indices:
                indices.append(i)
                break
            if len(indices) >= cap:
                break
        indices.sort()
    return [messages[i] for i in indices[:cap]]


def partition_for_profile(messages: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    """将全部消息分块送分析；过多时在全体上均匀抽样后再分块。"""
    n = len(messages)
    if n <= CHUNK_SIZE:
        return [messages]

    max_items = CHUNK_SIZE * MAX_CHUNKS
    pool = even_sample(messages, max_items) if n > max_items else messages

    chunks: list[list[dict[str, str]]] = []
    for i in range(0, len(pool), CHUNK_SIZE):
        chunks.append(pool[i : i + CHUNK_SIZE])
    return chunks


def sample_for_context(messages: list[dict[str, str]], cap: int) -> list[dict[str, str]]:
    """发送前辅助：从全部材料中均匀节选，不用末尾几条代替全体。"""
    if len(messages) <= cap:
        return messages
    return even_sample(messages, cap)
