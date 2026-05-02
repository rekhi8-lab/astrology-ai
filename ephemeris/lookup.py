import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent / "parsed"


def get_ephemeris(date: str) -> dict | None:
    try:
        year = date[:4]
        file_path = BASE_DIR / f"{year}.json"

        if not file_path.exists():
            return None

        with open(file_path, "r") as f:
            data = json.load(f)

        return data.get(date)

    except Exception as e:
        print("Error:", e)
        return None