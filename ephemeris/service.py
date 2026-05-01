from __future__ import annotations

from ephemeris.date_parser import extract_date
from ephemeris.lookup import get_ephemeris


def resolve_ephemeris(query: str) -> str | None:
    date = extract_date(query)
    if not date:
        return None

    values = get_ephemeris(date)
    if not values:
        return None

    lines = [f"Date: {date}"]
    for planet, value in values.items():
        lines.append(f"{planet.capitalize()}: {value}")
    return "\n".join(lines)
