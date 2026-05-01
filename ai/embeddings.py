from __future__ import annotations

import logging
from hashlib import md5

from chromadb.utils import embedding_functions


logger = logging.getLogger(__name__)


def build_embedding_function():
    try:
        return embedding_functions.DefaultEmbeddingFunction()
    except Exception:
        logger.exception("Falling back to Chroma default server-side embeddings")
        return None


def generate_id(text: str) -> str:
    return md5(text.encode("utf-8")).hexdigest()
