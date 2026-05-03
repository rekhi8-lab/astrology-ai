from __future__ import annotations

import json
from pathlib import Path

# Absolute degree offset for each sign (Aries = 0°)
SIGN_DEGREES: dict[str, float] = {
    "aries": 0.0,
    "taurus": 30.0,
    "gemini": 60.0,
    "cancer": 90.0,
    "leo": 120.0,
    "virgo": 150.0,
    "libra": 180.0,
    "scorpio": 210.0,
    "sagittarius": 240.0,
    "capricorn": 270.0,
    "aquarius": 300.0,
    "pisces": 330.0,
}

# Aspect definitions: angle → (name, max_orb)
ASPECTS: list[tuple[float, str, float]] = [
    (0.0,   "conjunction",  5.0),
    (60.0,  "sextile",      4.0),
    (90.0,  "square",       5.0),
    (120.0, "trine",        5.0),
    (180.0, "opposition",   5.0),
]

_SLOW_PLANETS = {"saturn", "jupiter", "pluto"}
_PERSONAL_PLANETS = {"sun", "moon", "mars", "mercury", "venus"}

NATAL_PATH = Path(__file__).resolve().parent.parent / "ephemeris" / "natal_chart.json"


def sign_to_absolute(sign: str, within_sign_degree: float) -> float:
    """Convert sign + within-sign degree to absolute ecliptic degree (0–360)."""
    offset = SIGN_DEGREES.get(sign.lower())
    if offset is None:
        raise ValueError(f"Unknown sign: {sign!r}")
    return offset + within_sign_degree


def calculate_aspect(transit_deg: float, natal_deg: float) -> tuple[str, float] | None:
    """
    Return (aspect_name, orb) if the two degrees form a recognised aspect,
    otherwise None.  Both values must be absolute degrees (0–360).
    """
    diff = abs(transit_deg - natal_deg) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff

    for angle, name, max_orb in ASPECTS:
        orb = abs(diff - angle)
        if orb <= max_orb:
            return name, round(orb, 2)
    return None


def get_aspect_priority(transit_planet: str, natal_planet: str, orb: float) -> str:
    """
    Return HIGH / MEDIUM / LOW priority for an aspect.

    Rules (in order of precedence):
    - Orb ≤ 1°            → HIGH  (tight regardless of planets)
    - Slow transit + orb ≤ 2° → HIGH
    - Personal transit + orb ≤ 2° → MEDIUM
    - Orb ≤ 3°            → MEDIUM
    - Otherwise           → LOW
    """
    t = transit_planet.lower()
    if orb <= 1.0:
        return "HIGH"
    if t in _SLOW_PLANETS and orb <= 2.0:
        return "HIGH"
    if t in _PERSONAL_PLANETS and orb <= 2.0:
        return "MEDIUM"
    if orb <= 3.0:
        return "MEDIUM"
    return "LOW"


def map_house_activation(transit_planet: str, natal_planet: str, natal_house: int | str) -> str:
    """Return a human-readable house-activation label."""
    return f"{natal_planet} activates House {natal_house}"


def get_natal_positions() -> dict[str, float]:
    """
    Load natal_chart.json and return planet → absolute-degree mapping.
    Kept for backwards-compatibility; prefer get_natal_data().
    """
    data = get_natal_data()
    return {planet: info["deg"] for planet, info in data.items()}


def get_natal_data() -> dict[str, dict]:
    """
    Load natal_chart.json and return a structured mapping:
        { "saturn": {"deg": 201.8, "house": 2, "sign": "Libra"}, ... }

    Ascendant and Midheaven are included with house = "-" when absent.
    """
    if not NATAL_PATH.exists():
        return {}

    with open(NATAL_PATH, "r", encoding="utf-8") as fh:
        chart: dict = json.load(fh)

    result: dict[str, dict] = {}
    for planet, data in chart.items():
        try:
            abs_deg = sign_to_absolute(data["sign"], data["degree"])
            result[planet] = {
                "deg": abs_deg,
                "house": data.get("house", "-"),
                "sign": data["sign"],
            }
        except (KeyError, ValueError):
            pass
    return result


def detect_aspects(
    transit_positions: dict[str, float],
    natal_data: dict[str, dict] | None = None,
) -> list[str]:
    """
    Compare each transit planet against every natal planet.

    Returns a list of structured strings ordered by priority (HIGH first):

        [HIGH] Transit Saturn opposition Natal Mars (orb 0.67°) → activates House 1
        [HIGH] Transit Mars square Natal Sun (orb 0.19°) → activates House 4
        [LOW]  Transit Moon conjunction Natal Uranus (orb 0.39°) → activates House 3
    """
    if natal_data is None:
        natal_data = get_natal_data()

    if not natal_data:
        return []

    _PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

    raw: list[tuple[int, str]] = []

    for t_planet, t_deg in transit_positions.items():
        for n_planet, n_info in natal_data.items():
            n_deg = n_info["deg"]
            n_house = n_info["house"]

            result = calculate_aspect(t_deg, n_deg)
            if result is None:
                continue

            aspect_name, orb = result
            priority = get_aspect_priority(t_planet, n_planet, orb)

            line = (
                f"[{priority}] Transit {t_planet.capitalize()} {aspect_name} "
                f"Natal {n_planet.capitalize()} (orb {orb}°) "
                f"→ activates House {n_house}"
            )
            raw.append((_PRIORITY_ORDER[priority], line))

    raw.sort(key=lambda x: x[0])
    return [line for _, line in raw]
