from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    telegram_token: str | None = os.getenv("TELEGRAM_TOKEN")
    claude_api_key: str | None = os.getenv("CLAUDE_API_KEY")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")

    top_k: int = _get_int("TOP_K", 4)
    max_retrieval_time: float = _get_float("MAX_RETRIEVAL_TIME", 1.5)
    max_ai_time: float = _get_float("MAX_AI_TIME", 60.0)
    daily_cost_limit: float = _get_float("DAILY_COST_LIMIT", 100.0)

    chroma_path: str = os.getenv("CHROMA_PATH", str(BASE_DIR / "chroma"))
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "astro_memory")

    google_sheet_name: str | None = os.getenv("GOOGLE_SHEET_NAME")
    google_service_account_json: str | None = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    requests_timeout: float = _get_float("REQUESTS_TIMEOUT", 12.0)
    max_chunk_chars: int = _get_int("MAX_CHUNK_CHARS", 900)
    chunk_overlap_chars: int = _get_int("CHUNK_OVERLAP_CHARS", 120)

    anthropic_input_per_million_usd: float = _get_float(
        "ANTHROPIC_INPUT_PER_MILLION_USD", 3.0
    )
    anthropic_output_per_million_usd: float = _get_float(
        "ANTHROPIC_OUTPUT_PER_MILLION_USD", 15.0
    )
    usd_to_inr: float = _get_float("USD_TO_INR", 83.0)

    def require_runtime_secrets(self) -> None:
        missing = []
        if not self.telegram_token:
            missing.append("TELEGRAM_TOKEN")
        if not self.claude_api_key:
            missing.append("CLAUDE_API_KEY")
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(f"Missing required environment variables: {joined}")

    def parsed_google_service_account(self) -> dict | None:
        if not self.google_service_account_json:
            return None
        try:
            return json.loads(self.google_service_account_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON") from exc


settings = Settings()
