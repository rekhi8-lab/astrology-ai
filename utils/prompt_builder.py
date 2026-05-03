from __future__ import annotations

from ephemeris.natal_loader import load_natal_chart


def build_prompt(
    user_input: str,
    context_chunks: list[dict],
    user_profile: dict | None = None,
    relevant_insights: list[dict] | None = None,
    ephemeris_context: str = "",
    user_profile_block: str | None = None,
    history_summary: str = "",
    aspects_summary: list[str] | None = None,
) -> str:

    natal_chart = load_natal_chart()

    _KEY_PLANETS = ["sun", "moon", "mercury", "venus", "mars", "jupiter",
                    "saturn", "ascendant", "midheaven"]

    def _build_natal_section(chart: dict | None) -> str:
        if not chart:
            return "Not available."
        lines = []
        for planet in _KEY_PLANETS:
            data = chart.get(planet)
            if data:
                label = planet.capitalize()
                lines.append(
                    f"{label}: {data['degree']:.1f}° {data['sign']} (House {data.get('house', '-')})"
                )
        return "\n".join(lines) if lines else "Not available."

    profile_block = user_profile_block or ""

    _INSTRUCTION = (
        "You are a personalised astrologer.\n\n"
        "The user's complete and verified birth chart is provided below.\n"
        "All required birth data is already available.\n\n"
        "Use the full birth chart for context and personality understanding.\n\n"
        "Base interpretation priority strictly on:\n"
        "1. Dasha (primary timing)\n"
        "2. Dominant transit aspects (filtered and ranked)\n"
        "3. Natal chart (supporting context)\n\n"
        "Ensure:\n"
        "- Accurate distinction between natal and transit positions.\n"
        "  Example: 'Natal Saturn is in Libra (House 2); transit Saturn is currently in Aries.'\n"
        "- Explicit mention of aspects (opposition, square, trine, etc.) when provided.\n"
        "- No incorrect assignment of transiting planets to natal houses.\n"
        "- Reference to Rahu, Ketu, and Chiron when contextually relevant.\n\n"
        "Focus on the most dominant influences. Avoid unnecessary detail.\n"
        "Do not request or assume missing birth information."
    )

    _history_section = (
        f"Conversation Context (summary):\n{history_summary}"
        if history_summary
        else ""
    )

    # --- Aspects block (shared between fast and full path) ---
    _aspects_section = (
        "Astrological Aspects (auto-calculated, orb ≤5°):\n"
        + "\n".join(f"  • {line}" for line in aspects_summary)
        if aspects_summary
        else ""
    )

    # --- Fast mode: bypass full prompt when ephemeris is available ---
    if ephemeris_context:
        parts = [_INSTRUCTION, profile_block, _history_section,
                 f"Current Transits:\n{ephemeris_context}",
                 _aspects_section,
                 f"Question:\n{user_input}"]
        return "\n\n".join(p for p in parts if p).strip()

    # --- Full natal section for non-fast path ---
    natal_section = (
        "User Birth Chart (on file):\n" + _build_natal_section(natal_chart)
        if natal_chart
        else "No natal chart available."
    )

    # --- Context block ---
    context = "\n\n".join(
        f"[Context {index + 1}]\n{item['text']}"
        for index, item in enumerate(context_chunks)
    )

    # --- User profile ---
    profile = user_profile or {}
    frequent_topics = ", ".join(profile.get("frequent_topics", [])) or "None yet"
    depth_preference = profile.get("depth_preference", "short")

    # --- Insights ---
    insights = relevant_insights or []
    insight_block = "\n".join(
        f"- {item['metadata'].get('interpretation', item['text'])}"
        for item in insights[:1]
    )

    insights_section = (
        "Previously, the user expressed:\n" + insight_block
        if insight_block
        else "No directly relevant prior insights."
    )

    # --- Ephemeris section ---
    ephemeris_section = (
        f"Relevant planetary positions:\n{ephemeris_context}"
        if ephemeris_context
        else "No ephemeris data provided."
    )

    # --- Final prompt ---
    return f"""{_INSTRUCTION}

{profile_block}

{_history_section + chr(10) if _history_section else ""}Guidelines:
- Use the natal chart above for all interpretations.
- Use ephemeris data when available.
- Refer to planetary signs explicitly.
- Compare transits with natal placements.
- Keep the explanation clear, grounded, and non-generic.

User preferences:
- Preferred depth: {depth_preference}
- Frequently asked topics: {frequent_topics}

User insights:
{insights_section}

Retrieved context:
{context or "No prior context found."}

{ephemeris_section}

{_aspects_section + chr(10) if _aspects_section else ""}{natal_section}

User question:
{user_input}""".strip()
