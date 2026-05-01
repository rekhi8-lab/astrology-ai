from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import fitz


PLANETS = [
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
]

MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"
PARSED_DIR = BASE_DIR / "parsed"


def parse_ephemeris_pdf(pdf_path: str | Path) -> dict:
    text = _extract_pdf_text(pdf_path)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    parsed: dict[str, dict[str, str]] = {}
    current_year = _guess_year(pdf_path, text)
    current_month: int | None = None

    for line in lines:
        month_match = re.search(
            r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b",
            line.lower(),
        )
        if month_match:
            current_month = MONTHS[month_match.group(1)]

        dated = _parse_dated_line(line)
        if dated:
            date_key, values = dated
            if values:
                parsed[date_key] = values
            continue

        inferred = _parse_day_row(line, current_year, current_month)
        if inferred:
            date_key, values = inferred
            if values:
                parsed[date_key] = values

    return parsed


def save_ephemeris_data(data: dict) -> list[Path]:
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    by_year: dict[str, dict] = {}
    for date_key, values in data.items():
        year = date_key.split("-", 1)[0]
        by_year.setdefault(year, {})[date_key] = values

    saved_paths: list[Path] = []
    for year, rows in by_year.items():
        target = PARSED_DIR / f"{year}.json"
        existing = {}
        if target.exists():
            try:
                existing = json.loads(target.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = {}

        existing.update(rows)
        target.write_text(json.dumps(existing, indent=2, sort_keys=True), encoding="utf-8")
        saved_paths.append(target)

    return saved_paths


def _extract_pdf_text(pdf_path: str | Path) -> str:
    parts: list[str] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            parts.append(page.get_text())
    return "\n".join(parts)


def _guess_year(pdf_path: str | Path, text: str) -> int:
    for source in (str(pdf_path), text[:500]):
        match = re.search(r"\b(20\d{2})\b", source)
        if match:
            return int(match.group(1))
    return datetime.utcnow().year


def _parse_dated_line(line: str) -> tuple[str, dict[str, str]] | None:
    patterns = [
        r"\b(?P<year>20\d{2})[-/](?P<month>\d{1,2})[-/](?P<day>\d{1,2})\b",
        r"\b(?P<day>\d{1,2})[-/](?P<month>\d{1,2})[-/](?P<year>20\d{2})\b",
        r"\b(?P<day>\d{1,2})\s+(?P<month_name>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(?P<year>20\d{2})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, line, flags=re.IGNORECASE)
        if not match:
            continue

        year = int(match.group("year"))
        if "month_name" in match.groupdict() and match.group("month_name"):
            month = MONTHS[match.group("month_name")[:3].lower()]
        else:
            month = int(match.group("month"))
        day = int(match.group("day"))
        date_key = f"{year:04d}-{month:02d}-{day:02d}"
        remainder = line[match.end():].strip()
        return date_key, _extract_planet_values(remainder)
    return None


def _parse_day_row(line: str, year: int, month: int | None) -> tuple[str, dict[str, str]] | None:
    if month is None:
        return None

    match = re.match(r"^(?P<day>\d{1,2})\s+(?P<rest>.+)$", line)
    if not match:
        return None

    day = int(match.group("day"))
    rest = match.group("rest")
    date_key = f"{year:04d}-{month:02d}-{day:02d}"
    values = _extract_planet_values(rest)
    return (date_key, values) if values else None


def _extract_planet_values(text: str) -> dict[str, str]:
    compact = " ".join(text.split())
    if not compact:
        return {}

    tokens = re.split(r"\s{2,}|\s(?=\d)|\s(?=[A-Za-z]{1,3}\b)", compact)
    cleaned = [token.strip(" |") for token in tokens if token.strip(" |")]
    values: dict[str, str] = {}

    for planet, value in zip(PLANETS, cleaned):
        if not value:
            continue
        values[planet] = value

    return values
