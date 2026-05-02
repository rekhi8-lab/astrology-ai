from __future__ import annotations

import json
import re
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

SIGNS = {
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
}

SIGN_MAP = {
    "ar": "aries", "ta": "taurus", "ge": "gemini", "cn": "cancer",
    "le": "leo", "vi": "virgo", "li": "libra", "sc": "scorpio",
    "sa": "sagittarius", "cp": "capricorn", "aq": "aquarius", "pi": "pisces",
}

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

SIGN_LETTER_MAP = {
    "a": "aries",
    "b": "taurus",
    "c": "gemini",
    "d": "cancer",
    "e": "leo",
    "f": "virgo",
    "g": "libra",
    "h": "scorpio",
    "i": "sagittarius",
    "j": "capricorn",
    "k": "aquarius",
    "l": "pisces",
}

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"
PARSED_DIR = BASE_DIR / "parsed"


def extract_text(pdf_path: str | Path) -> str:
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def parse_ephemeris_tokens(pdf_path: str | Path) -> dict[str, dict[str, str]]:
    pdf_path = Path(pdf_path)
    text = extract_text(pdf_path)
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    print("Total lines extracted:", len(lines))
    year = _guess_year(pdf_path)
    data: dict[str, dict[str, str]] = {}
    current_month: int | None = None
    detected_rows = 0

    for line in lines:
        current_month = _detect_month(line, current_month)
        row_match = re.match(r"^[A-Z]\s*(\d{1,2})\b", line)
        if not row_match or current_month is None:
            continue

        detected_rows += 1
        day = int(row_match.group(1))
        date_key = f"{year:04d}-{current_month:02d}-{day:02d}"
        row_body = line[row_match.end():].strip()
        row_body = re.sub(r"\s+\d{1,2}\s*$", "", row_body)
        values = _extract_planet_values(row_body)
        if len(values) >= 8:
            data[date_key] = values

    print("Total rows detected:", detected_rows)
    print("Total valid rows parsed:", len(data))
    if data:
        sample_key = next(iter(sorted(data)))
        print("Sample row:", {sample_key: data[sample_key]})
    return data


def save_json(data: dict[str, dict[str, str]], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, indent=2, sort_keys=True)


def run(pdf_path: str | Path) -> dict[str, dict[str, str]]:
    pdf_path = Path(pdf_path)
    data = parse_ephemeris_tokens(pdf_path)
    year = _guess_year(pdf_path)
    output_path = PARSED_DIR / f"{year}.json"
    save_json(data, output_path)
    print("Total rows parsed:", len(data))
    return data


def run_all() -> dict[str, int]:
    summary: dict[str, int] = {}
    for pdf_path in sorted(RAW_DIR.glob("*.pdf")):
        data = run(pdf_path)
        summary[pdf_path.name] = len(data)
    return summary


def _guess_year(pdf_path: Path) -> int:
    match = re.search(r"\b(20\d{2})\b", pdf_path.name)
    if match:
        return int(match.group(1))
    return 2025


def _detect_month(line: str, current_month: int | None) -> int | None:
    month_match = re.search(
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b",
        line.lower(),
    )
    if month_match:
        return MONTHS[month_match.group(1)]
    return current_month


def _extract_planet_values(row_text: str) -> dict[str, str]:
    cleaned = row_text.strip()
    print("RAW ROW:", row_text[:120])
    pattern = re.compile(r"(\d{1,2})\s*([a-lA-L])")
    matches = pattern.findall(cleaned)
    print("MATCHES FOUND:", matches[:10])

    values_list = []

    for degree, sign_letter in matches:
        sign = SIGN_LETTER_MAP.get(sign_letter.lower())
        if sign:
            values_list.append(f"{degree} {sign}")

    if len(matches) < 8:
        fallback = re.findall(r"(\d{1,2})°", cleaned)
        for degree in fallback:
            values_list.append(f"{degree} unknown")

    print("Extracted values:", values_list[:10])

    if len(values_list) < 8:
        return {}

    values_list = values_list[:10]

    values: dict[str, str] = {}
    for planet, value in zip(PLANETS, values_list):
        values[planet] = value

    return values


def _clean_token(token: str) -> str:
    token = token.strip()
    token = token.strip("|")
    token = re.sub(r"\s+", " ", token)
    return token


if __name__ == "__main__":
    run_all()
