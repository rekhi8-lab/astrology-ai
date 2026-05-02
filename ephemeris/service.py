from __future__ import annotations

from ephemeris.date_parser import extract_date
from ephemeris.lookup import get_ephemeris


def resolve_ephemeris(query: str) -> str | None:
    print("Query:", query)
    date = extract_date(query)
    print("Parsed date:", date)
    if not date:
        return None

    values = get_ephemeris(date)
    print("Lookup result:", values)
    if not values:
        return None

    lines = [f"Date: {date}"]
    for planet, value in values.items():
        lines.append(f"{planet.capitalize()}: {value}")
    return "\n".join(lines)
