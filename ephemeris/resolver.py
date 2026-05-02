from ephemeris.lookup import get_ephemeris
from ephemeris.formatter import format_position
from ephemeris.date_parser import extract_date  # you already built this


def build_ephemeris_context(user_text: str) -> str | None:
    date = extract_date(user_text)
    if not date:
        return None

    data = get_ephemeris(date)
    if not data:
        return None

    lines = [f"Ephemeris for {date}:"]
    for planet, value in data.items():
        lines.append(f"{planet.capitalize()}: {format_position(value)}")

    return "\n".join(lines)