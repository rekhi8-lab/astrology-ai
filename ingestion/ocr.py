from __future__ import annotations

from pathlib import Path

import pytesseract
from PIL import Image


def extract_text_from_image(file_path: str | Path) -> str:
    img = Image.open(file_path)
    return pytesseract.image_to_string(img)
