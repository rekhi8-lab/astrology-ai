from __future__ import annotations

from memory.user_profiles import KNOWN_TOPICS, extract_topics


GENERIC_REPLIES = {
    "yes",
    "yeah",
    "okay",
    "ok",
    "sure",
    "got it",
    "understood",
}

CONFUSED_MARKERS = {"confused", "unclear", "not sure", "don't understand", "hard to see"}
UNCERTAIN_MARKERS = {"maybe", "perhaps", "i guess", "it seems"}
POSITIVE_MARKERS = {"i understand", "that makes sense", "i can see", "resonates"}
INSIGHTFUL_MARKERS = {"i realized", "this relates", "this connects", "in my case", "i think"}


def extract_user_insight(user_message: str, user_profile: dict) -> dict | None:
    cleaned = " ".join((user_message or "").split())
    lowered = cleaned.lower()

    if len(cleaned) <= 30 or lowered in GENERIC_REPLIES:
        return None

    topic = _infer_topic(lowered, user_profile)
    interpretation = _infer_interpretation(cleaned, topic)
    if not interpretation:
        return None

    insight = {
        "type": "insight",
        "topic": topic,
        "interpretation": interpretation,
        "confidence": _infer_confidence(lowered, topic),
    }

    sentiment = _infer_sentiment(lowered)
    if sentiment:
        insight["sentiment"] = sentiment

    recent_insights = list(user_profile.get("recent_insights", []))
    recent_insights.append(
        {
            "topic": topic,
            "interpretation": interpretation,
            "confidence": insight["confidence"],
        }
    )
    user_profile["recent_insights"] = recent_insights[-3:]
    return insight


def _infer_topic(lowered: str, user_profile: dict) -> str:
    for topic in KNOWN_TOPICS:
        if topic in lowered:
            return topic

    topics = extract_topics(lowered)
    if topics:
        return topics[0]

    frequent_topics = user_profile.get("frequent_topics", [])
    if frequent_topics:
        return frequent_topics[0]

    return "general reflection"


def _infer_interpretation(user_message: str, topic: str) -> str | None:
    lowered = user_message.lower()

    if "because" in lowered:
        fragment = user_message.split("because", 1)[1].strip(" .,:;")
        if fragment:
            return f"user connects {topic} with {fragment[:120].lower()}"

    if "feels like" in lowered:
        fragment = user_message.lower().split("feels like", 1)[1].strip(" .,:;")
        if fragment:
            return f"user experiences {topic} as {fragment[:120]}"

    if "this relates" in lowered or "this connects" in lowered:
        return f"user links {topic} to a personal pattern or prior learning"

    if "i think" in lowered or "i feel" in lowered or "in my case" in lowered:
        return f"user reflects on {topic} through personal experience"

    words = user_message.split()
    if len(words) >= 8:
        snippet = " ".join(words[:14]).strip(" .,:;")
        return f"user sees {topic} as {snippet.lower()}"

    return None


def _infer_sentiment(lowered: str) -> str | None:
    if any(marker in lowered for marker in CONFUSED_MARKERS):
        return "confused"
    if any(marker in lowered for marker in UNCERTAIN_MARKERS):
        return "uncertain"
    if any(marker in lowered for marker in POSITIVE_MARKERS):
        return "positive"
    if any(marker in lowered for marker in INSIGHTFUL_MARKERS):
        return "insightful"
    return None


def _infer_confidence(lowered: str, topic: str) -> str:
    if topic in KNOWN_TOPICS and (
        "because" in lowered or "i realized" in lowered or "this relates" in lowered
    ):
        return "high"
    if "maybe" in lowered or "it seems" in lowered or topic == "general reflection":
        return "low"
    return "medium"
