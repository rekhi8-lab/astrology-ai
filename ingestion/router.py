from __future__ import annotations

import asyncio
from pathlib import Path

from telegram import Message

from ingestion.ocr import extract_text_from_image
from ingestion.pdf_parser import extract_text_from_pdf
from ingestion.scraper import extract_text_from_url
from utils.helpers import delete_file, download_telegram_file, extract_first_url, read_text_file


async def process_input(message: Message) -> str:
    if message.photo:
        file_path = await download_telegram_file(message.bot, message.photo[-1].file_id, ".jpg")
        try:
            return await asyncio.to_thread(extract_text_from_image, file_path)
        finally:
            delete_file(file_path)

    if message.document:
        suffix = Path(message.document.file_name or "upload.bin").suffix.lower()
        file_path = await download_telegram_file(message.bot, message.document.file_id, suffix)
        try:
            if suffix == ".pdf" or message.document.mime_type == "application/pdf":
                return await asyncio.to_thread(extract_text_from_pdf, file_path)
            if message.document.mime_type and message.document.mime_type.startswith("image/"):
                return await asyncio.to_thread(extract_text_from_image, file_path)
            return await asyncio.to_thread(read_text_file, file_path)
        finally:
            delete_file(file_path)

    text = message.text or message.caption or ""
    url = extract_first_url(text)
    if url:
        return await asyncio.to_thread(extract_text_from_url, url)

    if text.strip():
        return text

    raise ValueError("Unsupported message type. Send text, an image, a PDF, or a link.")
