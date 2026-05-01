from __future__ import annotations


def build_prompt(user_input: str, context_chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[Context {index + 1}]\n{item['text']}"
        for index, item in enumerate(context_chunks)
    )

    return f"""
You are a precise astrology teacher.

Rules:
- Default concise.
- Expand only if the user asks.
- Build on prior understanding.
- Avoid repetition.
- If context is weak or missing, say so briefly and answer carefully.

Retrieved context:
{context or "No prior context found."}

User question:
{user_input}
""".strip()
