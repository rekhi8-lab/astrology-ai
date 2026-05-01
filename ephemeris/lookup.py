from __future__ import annotations

from datetime import datetime

from ephemeris.loader import EPHEMERIS_DATA, load_ephemeris_data


def _normalize_date(value: str) -> str | None:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def get_ephemeris(date: str) -> dict[str, str] | None:
    if not EPHEMERIS_DATA:
        load_ephemeris_data()
    normalized = _normalize_date(date)
    if not normalized:
        return None
    return EPHEMERIS_DATA.get(normalized)


def get_range(start: str, end: str) -> dict[str, dict[str, str]]:
    if not EPHEMERIS_DATA:
        load_ephemeris_data()
    start_key = _normalize_date(start)
    end_key = _normalize_date(end)
    if not start_key or not end_key:
        return {}

    return {
        date_key: values
        for date_key, values in sorted(EPHEMERIS_DATA.items())
        if start_key <= date_key <= end_key
    }
