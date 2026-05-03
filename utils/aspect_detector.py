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

EXCLUDE_PLANETS = ["moon"]

STRONG_ASPECTS = ["opposition", "square"]
SUPPORTIVE_ASPECTS = ["trine", "sextile"]

HOUSE_MEANINGS: dict[int, str] = {
    1:  "identity, self, direction",
    2:  "money, income, resources",
    3:  "communication, thinking, environment",
    4:  "home, emotional foundation",
    5:  "creativity, expression, romance",
    6:  "work, health, routine",
    7:  "relationships, partnerships",
    8:  "transformation, shared resources",
    9:  "beliefs, expansion, learning",
    10: "career, public image",
    11: "gains, networks",
    12: "subconscious, isolation",
}

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


def get_aspect_priority(
    transit_planet: str,
    natal_planet: str,
    aspect: str,
    orb: float,
) -> str:
    """
    Score-based priority: HIGH / MEDIUM / LOW.

    Scoring:
      Orb  ≤ 1 → +3 | ≤ 2 → +2 | ≤ 3 → +1
      Hard aspect (opposition/square) → +3 | soft → +1
      Slow transit planet → +2
    """
    slow_planets = {"saturn", "jupiter", "pluto"}

    score = 0

    if orb <= 1.0:
        score += 3
    elif orb <= 2.0:
        score += 2
    elif orb <= 3.0:
        score += 1

    if aspect in STRONG_ASPECTS:
        score += 3
    elif aspect in SUPPORTIVE_ASPECTS:
        score += 1

    if transit_planet.lower() in slow_planets:
        score += 2

    if score >= 6:
        return "HIGH"
    if score >= 4:
        return "MEDIUM"
    return "LOW"


def generate_event_trigger(
    transit_planet: str,
    aspect: str,
    natal_planet: str,
    house: int | str,
) -> str:
    """Return a time-bounded event prediction for the aspect."""
    meaning = HOUSE_MEANINGS.get(house, "relevant life area") if isinstance(house, int) else "relevant life area"
    t = transit_planet.lower()

    if t == "saturn":
        return (
            f"Structural pressure building in {meaning}, "
            f"requiring discipline and restructuring over next 2–4 months"
        )
    if t == "mars":
        return (
            f"Immediate action, conflict, or decisive movement likely in {meaning} "
            f"within days to weeks"
        )
    if t == "jupiter":
        return (
            f"Opportunity, growth, or expansion opening in {meaning} "
            f"over the coming months"
        )
    return f"Noticeable activity or shift in {meaning}"


def get_natal_positions() -> dict[str, float]:
    """planet → absolute-degree mapping (backwards-compatible wrapper)."""
    return {planet: info["deg"] for planet, info in get_natal_data().items()}


def get_natal_data() -> dict[str, dict]:
    """
    Load natal_chart.json and return:
        { "saturn": {"deg": 201.8, "house": 2, "sign": "Libra"}, ... }
    """
    if not NATAL_PATH.exists():
        return {}

    with open(NATAL_PATH, "r", encoding="utf-8") as fh:
        chart: dict = json.load(fh)

    result: dict[str, dict] = {}
    for planet, data in chart.items():
        try:
            result[planet] = {
                "deg": sign_to_absolute(data["sign"], data["degree"]),
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
    Return up to 3 top-priority aspects as formatted strings, each followed
    by an event prediction.  Moon transits and LOW-priority signals excluded.

    Output format:
        [HIGH] Transit Saturn opposition Natal Mars (orb 0.67°) → activates House 1 (identity, self, direction)
        → Likely manifestation: Structural pressure building in ...
    """
    if natal_data is None:
        natal_data = get_natal_data()

    if not natal_data:
        return []

    raw: list[dict] = []

    for t_planet, t_deg in transit_positions.items():
        if t_planet.lower() in EXCLUDE_PLANETS:
            continue

        for n_planet, n_info in natal_data.items():
            n_deg = n_info["deg"]
            n_house = n_info["house"]

            result = calculate_aspect(t_deg, n_deg)
            if result is None:
                continue

            aspect_name, orb = result
            priority = get_aspect_priority(t_planet, n_planet, aspect_name, orb)

            if priority == "LOW":
                continue

            house_meaning = HOUSE_MEANINGS.get(n_house, "") if isinstance(n_house, int) else ""
            house_label = f"House {n_house} ({house_meaning})" if house_meaning else f"House {n_house}"

            event = generate_event_trigger(t_planet, aspect_name, n_planet, n_house)

            raw.append({
                "priority": priority,
                "text": (
                    f"[{priority}] Transit {t_planet.capitalize()} {aspect_name} "
                    f"Natal {n_planet.capitalize()} (orb {orb}°) "
                    f"→ activates {house_label}"
                ),
                "event": event,
            })

    # Sort HIGH before MEDIUM, then by insertion order (stable)
    priority_order = {"HIGH": 0, "MEDIUM": 1}
    raw.sort(key=lambda x: priority_order[x["priority"]])

    # Cap at top 3
    raw = raw[:3]

    formatted: list[str] = []
    for r in raw:
        formatted.append(r["text"])
        formatted.append(f"→ Likely manifestation: {r['event']}")

    return formatted
