from __future__ import annotations

from ephemeris.natal_loader import load_natal_chart


def build_prompt(
    user_input: str,
    context_chunks: list[dict],
    user_profile: dict | None = None,
    relevant_insights: list[dict] | None = None,
    ephemeris_context: str = "",
) -> str:

    natal_chart = load_natal_chart()

    # --- Fast mode: bypass full prompt when ephemeris is available ---
    if ephemeris_context:
        natal_section = (
            "\n".join(
                f"{planet.capitalize()}: {data['degree']:.1f}° {data['sign']} (House {data.get('house', '-')})"
                for planet, data in natal_chart.items()
                if planet in ["sun", "moon", "saturn", "mars"]
            )
            if natal_chart
            else "Not available."
        )
        return f"""You are an astrologer.

Transit:
{ephemeris_context}

Natal:
{natal_section}

Answer in EXACT structure:

1. Core Transit Insight (2–3 sentences)
2. Natal Impact (2–3 sentences)
3. Current Life Theme (2–3 sentences)
4. Final Takeaway (1–2 sentences)

Ensure ALL 4 sections are completed.
Do not leave the answer unfinished.
If response is cut, prioritize completing the Final Takeaway section.

Question:
{user_input}""".strip()

    # --- Compressed natal section (FIX 1) ---
    natal_section = (
        "User natal chart:\n" +
        "\n".join(
            f"{planet.capitalize()}: {data['degree']:.1f}° {data['sign']} (House {data.get('house', '-')})"
            for planet, data in natal_chart.items()
            if planet in ["sun", "moon", "saturn", "mars"]
        )
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
    return f"""
You are a personalized astrology learning companion.

Guidelines:
- Use ephemeris data when available.
- Refer to planetary signs explicitly.
- Treat the date as a real moment in time.
- When natal chart is available, compare transit with natal placements.
- Keep the explanation clear, grounded, and non-generic.

User profile:
- Preferred depth: {depth_preference}
- Frequently asked topics: {frequent_topics}

User insights:
{insights_section}

Retrieved context:
{context or "No prior context found."}

{ephemeris_section}

{natal_section}

User question:
{user_input}
""".strip()