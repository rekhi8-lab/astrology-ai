import swisseph as swe
from datetime import date, timedelta
import json
from pathlib import Path

# --- CONFIG ---

EPHE_PATH = "ephemeris/sweph"
OUTPUT_DIR = Path("ephemeris/parsed")

PLANETS = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mercury": swe.MERCURY,
    "venus": swe.VENUS,
    "mars": swe.MARS,
    "jupiter": swe.JUPITER,
    "saturn": swe.SATURN,
    "uranus": swe.URANUS,
    "neptune": swe.NEPTUNE,
    "pluto": swe.PLUTO,
}

START_YEAR = 1900
END_YEAR = 2100

# --- SETUP ---

swe.set_ephe_path(EPHE_PATH)

# Optional (Vedic)
# swe.set_sid_mode(swe.SIDM_LAHIRI)

# --- CORE ---

def generate_year(year):
    current = date(year, 1, 1)
    end = date(year, 12, 31)

    data = {}

    while current <= end:
        jd = swe.julday(current.year, current.month, current.day)

        day_data = {}

        for name, planet in PLANETS.items():
            result = swe.calc_ut(jd, planet)
            longitude = result[0][0]

            day_data[name] = round(longitude, 4)

        data[current.isoformat()] = day_data
        current += timedelta(days=1)

    return data


def save_year(year, data):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    path = OUTPUT_DIR / f"{year}.json"

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved {year}: {len(data)} days")


def run():
    for year in range(START_YEAR, END_YEAR + 1):
        data = generate_year(year)
        save_year(year, data)


if __name__ == "__main__":
    run()