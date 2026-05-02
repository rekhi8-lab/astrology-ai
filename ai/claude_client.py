from __future__ import annotations

import logging

import anthropic

from config import settings


logger = logging.getLogger(__name__)
client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global client
    if client is None:
        if not settings.claude_api_key:
            raise RuntimeError("CLAUDE_API_KEY is not configured")
        client = anthropic.Anthropic(api_key=settings.claude_api_key)
    return client


def generate_response(prompt: str, max_tokens: int = 300) -> tuple[str, object | None]:
    try:
        response = _get_client().messages.create(
            model=settings.claude_model,
            max_tokens=max_tokens,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}],
        )

        parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
        text = "\n".join(part for part in parts if part).strip()
        return text or "I could not generate a response.", response.usage
    except Exception:
        logger.exception("Claude generation failed")
        return "I hit an upstream model error while generating the response.", None
