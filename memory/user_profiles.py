from __future__ import annotations

import re
from collections import Counter


KNOWN_TOPICS = [
    "saturn return",
    "moon sign",
    "birth chart",
    "ascendant",
    "venus retrograde",
    "mercury retrograde",
]

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "please",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "why",
    "with",
}

SHORT_CUES = {"brief", "concise", "short", "quickly", "summary"}
DETAILED_CUES = {"why", "how", "explain"}

USER_PROFILES: dict[int, dict] = {}


def get_user_profile(user_id: int) -> dict:
    return USER_PROFILES.setdefault(
        user_id,
        {
            "message_count": 0,
            "topic_counts": {},
            "frequent_topics": [],
            "depth_score": 0,
            "depth_preference": "short",
        },
    )


def update_user_profile(user_id: int, text: str) -> dict:
    profile = get_user_profile(user_id)
    profile["message_count"] += 1

    for topic in extract_topics(text):
        profile["topic_counts"][topic] = profile["topic_counts"].get(topic, 0) + 1

    ranked_topics = Counter(profile["topic_counts"]).most_common(5)
    profile["frequent_topics"] = [topic for topic, _ in ranked_topics]
    profile["depth_score"] = _update_depth_score(text, profile["depth_score"])
    profile["depth_preference"] = _resolve_depth_preference(
        profile["depth_score"],
        profile["depth_preference"],
    )

    return profile


def extract_topics(text: str) -> list[str]:
    lowered = text.lower()
    matched_topics = [topic for topic in KNOWN_TOPICS if topic in lowered]
    if matched_topics:
        return matched_topics

    words = re.findall(r"[A-Za-z]{4,}", text.lower())
    return [word for word in words if word not in STOP_WORDS]


def _update_depth_score(text: str, current: int) -> int:
    lowered = text.lower()
    score = current

    score += sum(1 for cue in DETAILED_CUES if cue in lowered)
    score -= sum(1 for cue in SHORT_CUES if cue in lowered)
    return score


def _resolve_depth_preference(score: int, current: str) -> str:
    if score >= 2:
        return "detailed"
    if score <= -2:
        return "short"
    return current
