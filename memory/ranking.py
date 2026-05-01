from __future__ import annotations


def _priority(item: dict) -> tuple[int, int]:
    metadata = item.get("metadata", {})
    source_type = str(metadata.get("type", "")).lower()

    if "reflection" in source_type:
        return (0, metadata.get("chunk_index", 0))
    if "gold" in source_type:
        return (1, metadata.get("chunk_index", 0))
    if "interaction" in source_type:
        return (2, metadata.get("chunk_index", 0))
    return (3, metadata.get("chunk_index", 0))


def rank_context(chunks: list[dict]) -> list[dict]:
    return sorted(chunks, key=_priority)
