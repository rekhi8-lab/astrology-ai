from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from config import settings
from memory.chroma_db import collection

logger = logging.getLogger(__name__)
_AUDIT_LOG = Path(settings.chroma_path).parent / "memory_audit.log"


def _log_retrieval(query: str, hit_count: int) -> None:
    ts = datetime.utcnow().isoformat()
    entry = f"{ts} | RETRIEVE | hits={hit_count} | query={query[:120].replace(chr(10), ' ')}\n"
    try:
        with _AUDIT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(entry)
    except Exception:
        logger.warning("memory_audit.log retrieval write failed")


def _overlap_score(query: str, document: str) -> int:
    query_terms = {term for term in query.lower().split() if len(term) > 2}
    doc_terms = {term for term in document.lower().split() if len(term) > 2}
    return len(query_terms & doc_terms)


def _retrieval_score(query: str, item: dict) -> tuple[int, str]:
    metadata = item.get("metadata", {})
    return (
        _overlap_score(query, item.get("text", "")),
        str(metadata.get("stored_at", "")),
    )


def _insight_score(query: str, item: dict) -> tuple[int, str]:
    metadata = item.get("metadata", {})
    topic = str(metadata.get("topic", ""))
    interpretation = str(metadata.get("interpretation", ""))
    combined = f"{topic} {interpretation} {item.get('text', '')}".strip()
    return (
        _overlap_score(query, combined),
        str(metadata.get("stored_at", "")),
    )


def retrieve_context(query: str) -> list[dict]:
    target_count = min(max(settings.top_k, 3), 5)
    candidate_count = max(target_count, 5)
    results = collection.query(query_texts=[query], n_results=candidate_count)
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    retrieved: list[dict] = []
    for document, metadata in zip(documents, metadatas):
        if document:
            retrieved.append({"text": document, "metadata": metadata or {}})

    ranked = sorted(
        retrieved,
        key=lambda item: _retrieval_score(query, item),
        reverse=True,
    )
    result = ranked[:target_count]
    _log_retrieval(query, len(result))
    return result


def get_relevant_insights(user_id: int, query: str, limit: int = 2) -> list[dict]:
    candidate_count = max(limit * 2, 4)
    results = collection.query(
        query_texts=[query],
        n_results=candidate_count,
        where={"$and": [{"user_id": str(user_id)}, {"type": "insight"}]},
    )
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    retrieved: list[dict] = []
    for document, metadata in zip(documents, metadatas):
        if document and metadata:
            retrieved.append({"text": document, "metadata": metadata})

    ranked = sorted(retrieved, key=lambda item: _insight_score(query, item), reverse=True)
    filtered: list[dict] = []
    for item in ranked:
        overlap = _insight_score(query, item)[0]
        if overlap > 0 or not filtered:
            filtered.append(item)
        if len(filtered) >= limit:
            break

    return filtered[:limit]


def get_recent_insights(user_id: int, topic: str | None = None, limit: int = 3) -> list[dict]:
    candidate_count = max(limit * 3, 6)
    results = collection.get(
        where={"$and": [{"user_id": str(user_id)}, {"type": "insight"}]},
        limit=candidate_count,
        include=["documents", "metadatas"],
    )
    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])

    retrieved: list[dict] = []
    for document, metadata in zip(documents, metadatas):
        if document and metadata:
            retrieved.append({"text": document, "metadata": metadata})

    def sort_key(item: dict) -> tuple[int, str]:
        metadata = item.get("metadata", {})
        same_topic = 1 if topic and str(metadata.get("topic", "")) == topic else 0
        return (same_topic, str(metadata.get("stored_at", "")))

    ranked = sorted(retrieved, key=sort_key, reverse=True)
    return ranked[:limit]


def get_insight_sequence(user_id: int, topic: str | None = None, limit: int = 5) -> list[dict]:
    recent = get_recent_insights(user_id, topic=topic, limit=limit)
    chronological = sorted(
        recent,
        key=lambda item: str(item.get("metadata", {}).get("stored_at", "")),
    )
    return chronological[-limit:]
