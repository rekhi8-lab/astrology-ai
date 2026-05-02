from __future__ import annotations

from ephemeris.natal_loader import load_natal_chart


def build_prompt(
    user_input: str,
    context_chunks: list[dict],
    user_profile: dict | None = None,
    relevant_insights: list[dict] | None = None,
    ephemeris_context: str = "",
    user_profile_block: str | None = None,
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

    # --- Fast mode: bypass full prompt when ephemeris is available ---
    if ephemeris_context:
        return f"""You are a personalised astrologer.

{profile_block}

Current Transits:
{ephemeris_context}

Give a clear and complete answer in 2 short paragraphs.
End with a final conclusion sentence.

Question:
{user_input}""".strip()

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
    return f"""You are a personalised astrology learning companion.

{profile_block}

Guidelines:
- Use the natal chart provided above.
- Use ephemeris data when available.
- Refer to planetary signs explicitly.
- Treat the date as a real moment in time.
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

{natal_section}

User question:
{user_input}""".strip()
