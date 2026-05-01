from __future__ import annotations

from config import settings


def estimate_cost(usage: object | None) -> float:
    if not usage:
        return 0.0

    input_tokens = float(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = float(getattr(usage, "output_tokens", 0) or 0)

    usd_cost = (
        input_tokens / 1_000_000 * settings.anthropic_input_per_million_usd
        + output_tokens / 1_000_000 * settings.anthropic_output_per_million_usd
    )
    return round(usd_cost * settings.usd_to_inr, 2)
