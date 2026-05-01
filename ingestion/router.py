from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from telegram import Message

from ingestion.ocr import extract_text_from_image
from ingestion.pdf_parser import extract_text_from_pdf
from ingestion.scraper import extract_text_from_url
from utils.helpers import delete_file, download_telegram_file, extract_first_url, read_text_file


@dataclass
class ProcessedInput:
    text: str
    source_type: str
    should_store: bool = True


async def process_input(message: Message) -> ProcessedInput:
    if message.photo:
        file_path = await download_telegram_file(message.bot, message.photo[-1].file_id, ".jpg")
        try:
            text = await asyncio.to_thread(extract_text_from_image, file_path)
            return ProcessedInput(text=text, source_type="image_ocr")
        finally:
            delete_file(file_path)

    if message.document:
        suffix = Path(message.document.file_name or "upload.bin").suffix.lower()
        file_path = await download_telegram_file(message.bot, message.document.file_id, suffix)
        try:
            if suffix == ".pdf" or message.document.mime_type == "application/pdf":
                text = await asyncio.to_thread(extract_text_from_pdf, file_path)
                return ProcessedInput(text=text, source_type="pdf")
            if message.document.mime_type and message.document.mime_type.startswith("image/"):
                text = await asyncio.to_thread(extract_text_from_image, file_path)
                return ProcessedInput(text=text, source_type="image_ocr")
            text = await asyncio.to_thread(read_text_file, file_path)
            return ProcessedInput(text=text, source_type="document")
        finally:
            delete_file(file_path)

    text = message.text or message.caption or ""
    url = extract_first_url(text)
    if url:
        extracted = await asyncio.to_thread(extract_text_from_url, url)
        return ProcessedInput(text=extracted, source_type="url")

    if text.strip():
        return ProcessedInput(text=text, source_type="text")

    raise ValueError("Unsupported message type. Send text, an image, a PDF, or a link.")
