import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
NATAL_PATH = BASE_DIR / "natal_chart.json"


def load_natal_chart() -> dict | None:
    if not NATAL_PATH.exists():
        return None

    with open(NATAL_PATH, "r") as f:
        return json.load(f)