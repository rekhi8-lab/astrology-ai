from __future__ import annotations

import re
from datetime import datetime


def extract_date(query: str) -> str | None:
    query = query or ""

    numeric_match = re.search(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", query)
    if numeric_match:
        year, month, day = numeric_match.groups()
        date = f"{year}-{int(month):02d}-{int(day):02d}"
        print("Extracted date:", date)
        return date

    long_month_match = re.search(
        r"\b(\d{1,2})\s+"
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(20\d{2})\b",
        query,
        flags=re.IGNORECASE,
    )
    if long_month_match:
        day, month_name, year = long_month_match.groups()
        parsed = datetime.strptime(f"{day} {month_name} {year}", "%d %B %Y")
        date = parsed.strftime("%Y-%m-%d")
        print("Extracted date:", date)
        return date

    print("Extracted date:", None)
    return None
