from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from config import settings


def extract_text_from_url(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AstrologyAI/1.0; +https://railway.app)"
        )
    }
    response = requests.get(url, headers=headers, timeout=settings.requests_timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
