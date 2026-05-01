from __future__ import annotations

import re
import tempfile
from pathlib import Path

from config import settings


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def chunk_text(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunk_size = settings.max_chunk_chars
    overlap = settings.chunk_overlap_chars
    chunks: list[str] = []
    start = 0

    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(end - overlap, start + 1)

    return chunks


def extract_first_url(text: str) -> str | None:
    match = re.search(r"https?://\S+", text or "")
    return match.group(0) if match else None


def read_text_file(file_path: str | Path) -> str:
    return Path(file_path).read_text(encoding="utf-8", errors="ignore")


def delete_file(file_path: str | Path) -> None:
    try:
        Path(file_path).unlink(missing_ok=True)
    except OSError:
        pass


async def download_telegram_file(bot, file_id: str, suffix: str) -> str:
    ensure_directory(Path("tmp"))
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir="tmp")
    temp_file.close()

    telegram_file = await bot.get_file(file_id)
    await telegram_file.download_to_drive(custom_path=temp_file.name)
    return temp_file.name
