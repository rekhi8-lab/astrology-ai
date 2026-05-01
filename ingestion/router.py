from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from ingestion.ocr import extract_text_from_image
from ingestion.pdf_parser import extract_text_from_pdf
from ingestion.scraper import extract_text_from_url
from utils.helpers import extract_first_url, read_text_file

PDF_FOCUS_TERMS = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
    "asc",
    "ascendant",
    "house",
)
PDF_CHAR_LIMIT = 5000
PDF_LINE_LIMIT = 100
PDF_LOW_SIGNAL_MESSAGE = (
    "I could not extract clear chart data. Try asking a specific question like:\n\n"
    "* What is my Saturn placement?\n"
    "* What are my life themes?"
)


@dataclass
class ProcessedInput:
    text: str
    source_type: str
    should_store: bool = True


def _filter_pdf_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    focused_lines = [
        line for line in lines
        if any(term.lower() in line.lower() for term in PDF_FOCUS_TERMS)
    ]
    if len(focused_lines) < 10:
        fallback_lines = lines[:PDF_LINE_LIMIT]
        normalized = [" ".join(line.split()) for line in fallback_lines]
        return "\n".join(line for line in normalized if line).strip()

    filtered_lines = focused_lines[:PDF_LINE_LIMIT]
    normalized = [" ".join(line.split()) for line in filtered_lines]
    return "\n".join(line for line in normalized if line).strip()


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
            filtered_text = _filter_pdf_text(extracted)
            if not filtered_text.strip():
                return ProcessedInput(text=PDF_LOW_SIGNAL_MESSAGE, source_type="pdf", should_store=False)

            trimmed_text = filtered_text[:PDF_CHAR_LIMIT].strip()
            if len(trimmed_text.split()) < 8:
                return ProcessedInput(text=PDF_LOW_SIGNAL_MESSAGE, source_type="pdf", should_store=False)

            return ProcessedInput(text=trimmed_text, source_type="pdf")

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
