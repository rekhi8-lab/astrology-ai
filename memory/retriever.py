from __future__ import annotations

from memory.chroma_db import collection
from config import settings


def retrieve_context(query: str) -> list[dict]:
    results = collection.query(query_texts=[query], n_results=settings.top_k)
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    retrieved: list[dict] = []
    for document, metadata in zip(documents, metadatas):
        if document:
            retrieved.append({"text": document, "metadata": metadata or {}})

    return retrieved
