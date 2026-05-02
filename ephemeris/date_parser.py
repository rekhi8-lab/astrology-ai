from __future__ import annotations

import re
from datetime import datetime


def extract_date(text: str) -> str | None:
    text = (text or "").strip()

    # DD-MM-YYYY is the PRIMARY format; YYYY-MM-DD is secondary
    patterns_formats = [
        (r"\b\d{2}-\d{2}-\d{4}\b",                        ["%d-%m-%Y"]),
        (r"\b\d{4}-\d{2}-\d{2}\b",                        ["%Y-%m-%d"]),
        (r"\b\d{2}/\d{2}/\d{4}\b",                        ["%d/%m/%Y"]),
        (r"\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b",             ["%d %B %Y", "%d %b %Y"]),
        (r"\b[A-Za-z]+\s+\d{1,2},\s*\d{4}\b",            ["%B %d, %Y", "%b %d, %Y"]),
    ]

    for pattern, formats in patterns_formats:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(0)
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue

    return None
