from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PARSED_DIR = BASE_DIR / "parsed"
EPHEMERIS_DATA: dict[str, dict[str, str]] = {}


def load_ephemeris_data() -> dict[str, dict[str, str]]:
    data: dict[str, dict[str, str]] = {}

    if not PARSED_DIR.exists():
        EPHEMERIS_DATA.clear()
        print("Loaded ephemeris dates:", len(EPHEMERIS_DATA))
        return EPHEMERIS_DATA

    for path in sorted(PARSED_DIR.glob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as file_handle:
                payload = json.load(file_handle)
        except json.JSONDecodeError:
            continue
        for date_key, values in payload.items():
            if isinstance(values, dict):
                data[date_key] = values

    EPHEMERIS_DATA.clear()
    EPHEMERIS_DATA.update(data)
    print("Loaded ephemeris dates:", len(EPHEMERIS_DATA))
    return EPHEMERIS_DATA


def load_all() -> dict[str, dict[str, str]]:
    return load_ephemeris_data()


load_ephemeris_data()
