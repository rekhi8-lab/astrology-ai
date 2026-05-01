from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from ingestion.ocr import extract_text_from_image
from ingestion.pdf_parser import extract_text_from_pdf
from ingestion.scraper import extract_text_from_url
from utils.helpers import extract_first_url, read_text_file


@dataclass
class ProcessedInput:
    text: str
    source_type: str
    should_store: bool = True


def process_input(text: str | None = None, file_path: str | None = None) -> ProcessedInput:
    if file_path:
        suffix = Path(file_path).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            extracted = extract_text_from_image(file_path)
            if not extracted.strip():
                raise ValueError("Could not extract readable content from file")
            return ProcessedInput(text=extracted, source_type="image_ocr")
        if suffix == ".pdf":
            extracted = extract_text_from_pdf(file_path)
            if not extracted.strip():
                raise ValueError("Could not extract readable content from file")
            return ProcessedInput(text=extracted, source_type="pdf")

        extracted = read_text_file(file_path)
        if not extracted.strip():
            raise ValueError("Could not extract readable content from file")
        return ProcessedInput(text=extracted, source_type="document")

    text = text or ""
    url = extract_first_url(text)
    if url:
        extracted = extract_text_from_url(url)
        return ProcessedInput(text=extracted, source_type="url")

    if text.strip():
        return ProcessedInput(text=text, source_type="text")

    raise ValueError("Unsupported message type. Send text, an image, a PDF, or a link.")
