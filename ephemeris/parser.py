from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import fitz
from ingestion.pdf_parser import extract_text_from_pdf


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
    text = extract_text_from_pdf(pdf_path)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    print("Total lines extracted:", len(lines))

    parsed: dict[str, dict[str, str]] = {}
    current_year = _guess_year(pdf_path, text)
    current_month: int | None = None

    parsed.update(_parse_table_rows(pdf_path, current_year))

    for line in lines:
        current_month = _detect_month(line, current_month)

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

    parsed = dict(sorted(parsed.items()))
    print("Parsed rows:", len(parsed))
    if parsed:
        first_key = next(iter(parsed))
        print("Example parsed row:", {first_key: parsed[first_key]})
    if len(parsed) < 200:
        print("WARNING: Incomplete parse detected")
        print("Parser likely missing rows — check PDF layout")

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


def run_parser() -> dict[str, int]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    summary: dict[str, int] = {}
    for pdf_path in sorted(RAW_DIR.glob("*.pdf")):
        data = parse_ephemeris_pdf(pdf_path)
        save_ephemeris_data(data)
        summary[pdf_path.name] = len(data)
        print("Parsed days:", len(data))

    return summary


def _guess_year(pdf_path: str | Path, text: str) -> int:
    for source in (str(pdf_path), text[:500]):
        match = re.search(r"\b(20\d{2})\b", source)
        if match:
            return int(match.group(1))
    return datetime.utcnow().year


def _detect_month(text: str, current_month: int | None) -> int | None:
    month_match = re.search(
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b",
        text.lower(),
    )
    if month_match:
        return MONTHS[month_match.group(1)]
    return current_month


def _parse_table_rows(pdf_path: str | Path, year: int) -> dict[str, dict[str, str]]:
    parsed: dict[str, dict[str, str]] = {}
    current_month: int | None = None

    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                page_text = page.get_text("text", sort=True)
                for line in page_text.splitlines():
                    current_month = _detect_month(line, current_month)

                table_finder = page.find_tables()
                for table in getattr(table_finder, "tables", []):
                    for row in table.extract():
                        parsed_row = _parse_table_row(row, year, current_month)
                        if parsed_row:
                            date_key, values = parsed_row
                            parsed[date_key] = values
    except Exception:
        return {}

    return parsed


def _parse_table_row(
    row: list[str] | tuple[str, ...],
    year: int,
    current_month: int | None,
) -> tuple[str, dict[str, str]] | None:
    cleaned_cells = [_clean_cell(cell) for cell in row if _clean_cell(cell)]
    if len(cleaned_cells) < 2:
        return None

    row_text = " ".join(cleaned_cells)
    dated = _parse_dated_line(row_text)
    if dated:
        date_key, values = dated
        if len(values) >= 8:
            return date_key, values

    first_cell = cleaned_cells[0]
    if current_month is None or not re.match(r"^\d{1,2}$", first_cell):
        return None

    day = int(first_cell)
    values = _extract_planet_values(cleaned_cells[1:])
    if len(values) < 8:
        return None

    return _normalize_date(year, current_month, day), values


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
        date_key = _normalize_date(year, month, day)
        remainder = line[match.end():].strip()
        values = _extract_planet_values(remainder)
        if len(values) < 8:
            continue
        return date_key, values
    return None


def _parse_day_row(line: str, year: int, month: int | None) -> tuple[str, dict[str, str]] | None:
    if month is None:
        return None

    match = re.match(r"^\s*(?P<day>\d{1,2})\s+(?P<rest>.+)$", line)
    if not match:
        return None

    day = int(match.group("day"))
    rest = match.group("rest")
    date_key = _normalize_date(year, month, day)
    values = _extract_planet_values(rest)
    return (date_key, values) if len(values) >= 8 else None


def _extract_planet_values(source: str | list[str]) -> dict[str, str]:
    cleaned = _split_value_tokens(source)
    if len(cleaned) < 8:
        return {}

    values: dict[str, str] = {}
    for planet, value in zip(PLANETS, cleaned[: len(PLANETS)]):
        if not value:
            continue
        values[planet] = value

    return values


def _normalize_date(year: int, month: int, day: int) -> str:
    return f"{year:04d}-{month:02d}-{day:02d}"


def _split_value_tokens(source: str | list[str]) -> list[str]:
    if isinstance(source, list):
        return [_clean_cell(token) for token in source if _clean_cell(token)]

    compact = " ".join(source.split())
    if not compact:
        return []

    tokens = re.split(r"\s{2,}|\t+|\s\|\s|\|", source)
    cleaned = [_clean_cell(token) for token in tokens if _clean_cell(token)]
    if len(cleaned) >= 8:
        return cleaned

    fallback = re.split(r"\s+(?=[A-Za-z]{1,4}\s*\d)|\s{2,}", compact)
    return [_clean_cell(token) for token in fallback if _clean_cell(token)]


def _clean_cell(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).split()).strip(" |")
