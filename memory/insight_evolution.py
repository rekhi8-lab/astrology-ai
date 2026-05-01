from __future__ import annotations


NEGATION_MARKERS = {"not", "never", "no", "without", "isn't", "doesn't", "can't"}
SHIFT_MARKERS = {"now", "instead", "more", "deeper", "growth", "structure", "maturity"}


def compare_insights(current_insight: dict, past_insights: list[dict]) -> dict | None:
    if not past_insights:
        return None

    current_topic = str(current_insight.get("topic", ""))
    current_interpretation = str(current_insight.get("interpretation", "")).lower()

    best_match: dict | None = None
    best_score = -1
    for insight in past_insights:
        metadata = insight.get("metadata", {})
        past_interpretation = str(metadata.get("interpretation", "")).lower()
        score = _similarity_score(current_interpretation, past_interpretation)
        if str(metadata.get("topic", "")) == current_topic:
            score += 2
        if score > best_score:
            best_score = score
            best_match = insight

    if best_match is None:
        return None

    past_metadata = best_match.get("metadata", {})
    past_interpretation = str(past_metadata.get("interpretation", ""))
    evolution_type = _classify_evolution(current_interpretation, past_interpretation.lower())
    if evolution_type is None:
        return None

    return {
        "type": evolution_type,
        "summary": _build_summary(current_insight, past_interpretation, evolution_type),
    }


def _similarity_score(current: str, past: str) -> int:
    current_terms = {term for term in current.split() if len(term) > 3}
    past_terms = {term for term in past.split() if len(term) > 3}
    return len(current_terms & past_terms)


def _classify_evolution(current: str, past: str) -> str | None:
    current_terms = {term for term in current.split() if len(term) > 3}
    past_terms = {term for term in past.split() if len(term) > 3}
    overlap = len(current_terms & past_terms)

    current_negation = any(marker in current for marker in NEGATION_MARKERS)
    past_negation = any(marker in past for marker in NEGATION_MARKERS)
    if overlap > 0 and current_negation != past_negation:
        return "contradiction"

    current_shift = any(marker in current for marker in SHIFT_MARKERS)
    past_shift = any(marker in past for marker in SHIFT_MARKERS)
    if overlap >= 2 and (current_shift and not past_shift):
        return "shift"

    if overlap >= 3:
        return "reinforcement"

    if overlap >= 1 and current != past:
        return "shift"

    return None


def _build_summary(current_insight: dict, past_interpretation: str, evolution_type: str) -> str:
    topic = current_insight.get("topic", "this topic")
    current_interpretation = str(current_insight.get("interpretation", "this in a new way"))

    if evolution_type == "reinforcement":
        return (
            f"Your current view of {topic} reinforces an earlier pattern: "
            f"you’re returning to the same core understanding with more clarity."
        )
    if evolution_type == "contradiction":
        return (
            f"Your view of {topic} seems to push against an earlier interpretation, "
            f"suggesting a real change in how you're making sense of it."
        )
    return (
        f"Your understanding of {topic} seems to be shifting from "
        f"'{past_interpretation[:70]}' toward '{current_interpretation[:70]}'."
    )
