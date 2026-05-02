from __future__ import annotations

from datetime import datetime

from ephemeris.lookup import get_ephemeris
from ephemeris.formatter import format_position
from ephemeris.date_parser import extract_date


# Core planets we may use (ordered by importance)
PLANET_PRIORITY = [
    "saturn",
    "jupiter",
    "mars",
    "moon",
    "sun",
    "venus",
    "mercury",
]


def _select_relevant_planets(user_text: str, data: dict) -> list[str]:
    """
    Select a small, relevant subset of planets based on the user query.
    Keeps prompt lightweight and avoids model timeout.
    """

    text = user_text.lower()

    # Always include Saturn if query is about Saturn
    if "saturn" in text:
        base = ["saturn", "mars", "moon"]
    elif "jupiter" in text:
        base = ["jupiter", "moon", "sun"]
    elif "mars" in text:
        base = ["mars", "saturn", "moon"]
    else:
        base = ["sun", "moon", "saturn"]

    # Ensure only available planets are included
    selected = [p for p in base if p in data]

    # Safety: max 4 planets
    return selected[:4]


def build_ephemeris_context(user_text: str) -> str | None:
    """
    Build a compact, relevant ephemeris context block for the prompt.
    """
    from ephemeris.loader import EPHEMERIS_DATA
    print("EPHEMERIS TOTAL DATES:", len(EPHEMERIS_DATA))

    extracted = extract_date(user_text)
    date = extracted or datetime.utcnow().strftime("%Y-%m-%d")
    print("USER INPUT:", user_text)
    print("EXTRACTED DATE:", extracted)
    print("LOOKUP DATE:", date)

    data = get_ephemeris(date)
    if not data:
        print("EPHEMERIS RESULT: None")
        return None

    selected_planets = _select_relevant_planets(user_text, data)

    if not selected_planets:
        print("EPHEMERIS RESULT: no planets selected")
        return None

    lines = [f"Ephemeris for {date}:"]

    for planet in selected_planets:
        value = data.get(planet)
        if value is not None:
            formatted = format_position(value)
            lines.append(f"{planet.capitalize()}: {formatted}")

    result = "\n".join(lines)
    print("EPHEMERIS RESULT:", result)
    print("FAST MODE TRIGGERED" if result else "FAST MODE NOT TRIGGERED")
    return result