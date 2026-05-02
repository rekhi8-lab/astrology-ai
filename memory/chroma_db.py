from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import chromadb

from ai.embeddings import build_embedding_function, generate_id
from config import settings
from utils.helpers import chunk_text, ensure_directory


logger = logging.getLogger(__name__)

ensure_directory(Path(settings.chroma_path))
client = chromadb.PersistentClient(path=settings.chroma_path)
collection = client.get_or_create_collection(
    name=settings.chroma_collection,
    embedding_function=build_embedding_function(),
    metadata={"hnsw:space": "cosine"},
)

_AUDIT_LOG = Path(settings.chroma_path).parent / "memory_audit.log"


def _log_audit(event: str, content: str, metadata: dict) -> None:
    ts = datetime.utcnow().isoformat()
    entry = (
        f"{ts} | {event} | type={metadata.get('type', '?')} "
        f"| user={metadata.get('user_id', '?')} "
        f"| preview={content[:120].replace(chr(10), ' ')}\n"
    )
    try:
        with _AUDIT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(entry)
    except Exception:
        logger.warning("memory_audit.log write failed")


def get_collection():
    return collection


def store_documents(text: str, metadata: dict) -> None:
    chunks = chunk_text(text)
    if not chunks:
        return

    collection.upsert(
        documents=chunks,
        metadatas=[{**metadata, "chunk_index": index} for index, _ in enumerate(chunks)],
        ids=[generate_id(f"{metadata.get('type', 'memory')}::{index}::{chunk}") for index, chunk in enumerate(chunks)],
    )
    _log_audit("WRITE", text, metadata)


def store_interaction(user_input: str, response: str, metadata: dict) -> None:
    combined = f"User:\n{user_input}\n\nAssistant:\n{response}"
    store_documents(combined, metadata)


def is_valid_memory(text: str) -> bool:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return False
    if len(cleaned) < 30:
        return False
    if len(cleaned.split()) < 6:
        return False
    return True
