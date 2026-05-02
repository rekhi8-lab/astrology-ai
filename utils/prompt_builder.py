from __future__ import annotations


def build_prompt(
    user_input: str,
    context_chunks: list[dict],
    user_profile: dict | None = None,
    relevant_insights: list[dict] | None = None,
    ephemeris_context: str = "",
) -> str:
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
        for item in insights[:2]
    )

    insights_section = (
        "Previously, the user expressed:\n" + insight_block
        if insight_block
        else "No directly relevant prior insights."
    )

    # --- Ephemeris section (THIS is the key addition) ---
    ephemeris_section = (
        f"Relevant planetary positions:\n{ephemeris_context}"
        if ephemeris_context
        else "No ephemeris data provided."
    )

    # --- Final prompt ---
    return f"""
You are a personalized astrology learning companion.

Guidelines:
- Adapt explanation depth to user preference.
- Build on past topics if relevant.
- Avoid repeating basic explanations.
- Connect current answer with past learning when possible.
- If relevant, refer to past user insights to build continuity. Do not force it if unrelated.
- If context is weak or missing, say so briefly and answer carefully.
- Use ephemeris data when available to ground your interpretation in real planetary positions.
- Refer explicitly to planetary signs when explaining transits.

User profile:
- Preferred depth: {depth_preference}
- Frequently asked topics: {frequent_topics}

User insights:
{insights_section}

Retrieved context:
{context or "No prior context found."}

{ephemeris_section}

User question:
{user_input}
""".strip()