from __future__ import annotations

from pathlib import Path

import chromadb

from ai.embeddings import build_embedding_function, generate_id
from config import settings
from utils.helpers import chunk_text, ensure_directory


ensure_directory(Path(settings.chroma_path))
client = chromadb.PersistentClient(path=settings.chroma_path)
collection = client.get_or_create_collection(
    name=settings.chroma_collection,
    embedding_function=build_embedding_function(),
    metadata={"hnsw:space": "cosine"},
)


def store_documents(text: str, metadata: dict) -> None:
    chunks = chunk_text(text)
    if not chunks:
        return

    collection.upsert(
        documents=chunks,
        metadatas=[{**metadata, "chunk_index": index} for index, _ in enumerate(chunks)],
        ids=[generate_id(f"{metadata.get('type', 'memory')}::{index}::{chunk}") for index, chunk in enumerate(chunks)],
    )


def store_interaction(user_input: str, response: str, metadata: dict) -> None:
    combined = f"User:\n{user_input}\n\nAssistant:\n{response}"
    store_documents(combined, metadata)
