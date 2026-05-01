from __future__ import annotations

from pathlib import Path

import fitz


def extract_text_from_pdf(file_path: str | Path) -> str:
    text_parts: list[str] = []
    with fitz.open(file_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(part.strip() for part in text_parts if part.strip())
