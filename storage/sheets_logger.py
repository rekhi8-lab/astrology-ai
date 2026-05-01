from __future__ import annotations

import logging
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import settings


logger = logging.getLogger(__name__)

_sheet = None


def _get_sheet():
    global _sheet

    if _sheet is not None:
        return _sheet

    creds_data = settings.parsed_google_service_account()
    if not creds_data or not settings.google_sheet_name:
        return None

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_data, scope)
    client = gspread.authorize(creds)
    _sheet = client.open(settings.google_sheet_name).sheet1
    return _sheet


def log_entry(question: str, answer: str, cost: float) -> None:
    sheet = _get_sheet()
    if sheet is None:
        return

    try:
        sheet.append_row([datetime.utcnow().isoformat(), question, answer, cost])
    except Exception:
        logger.exception("Failed to append row to Google Sheets")
