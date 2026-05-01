from __future__ import annotations

from memory.user_profiles import extract_topics


REFLECTIONS = {
    "interpretation": [
        "Pause for a moment... how would you put this into your own words?",
        "If you had to explain this simply, what would you say it means?",
    ],
    "application": [
        "Pause for a moment... can you see this pattern in your own experiences?",
        "Where does this idea show up in real life for you?",
    ],
    "contradiction": [
        "What part of this feels unclear or a little counterintuitive?",
        "Is there any part of this that doesn't sit neatly with what you expected?",
    ],
    "connection": [
        "This touches your earlier interest in {top_topic}. Want to explore that link?",
        "There's a thread here with your past questions on {top_topic}. Should we follow it?",
    ],
}


def _has_topic_overlap(user_message: str, topics: list[str]) -> bool:
    lowered = user_message.lower()
    if any(topic in lowered for topic in topics):
        return True

    message_terms = {term for term in lowered.split() if len(term) > 2}
    for topic in topics:
        topic_terms = {term for term in topic.lower().split() if len(term) > 2}
        if message_terms & topic_terms:
            return True
    return False


def _select_reflection_type(
    user_profile: dict,
    user_message: str,
    ai_response: str,
) -> str:
    frequent_topics = user_profile.get("frequent_topics", [])
    recent_topics = user_profile.get("recent_topics", [])
    history = user_profile.get("reflection_history", [])
    last_type = history[-1] if history else ""

    overlap_topics = frequent_topics + recent_topics
    if _has_topic_overlap(user_message, overlap_topics):
        return "connection" if last_type != "connection" else "application"

    if len(ai_response) > 800:
        return "application"

    if user_profile.get("depth_preference", "short") == "detailed":
        preferred = "interpretation" if last_type != "interpretation" else "contradiction"
        return preferred if preferred != last_type else "application"

    return "application"


def _remember_topics(user_profile: dict, user_message: str) -> None:
    current_topics = extract_topics(user_message)
    if not current_topics:
        return

    recent_topics = list(user_profile.get("recent_topics", []))
    for topic in current_topics:
        if topic in recent_topics:
            recent_topics.remove(topic)
        recent_topics.append(topic)

    user_profile["recent_topics"] = recent_topics[-3:]


def _remember_reflection_type(user_profile: dict, reflection_type: str) -> None:
    history = list(user_profile.get("reflection_history", []))
    history.append(reflection_type)
    user_profile["reflection_history"] = history[-3:]


def _build_reflection(reflection_type: str, user_profile: dict) -> str:
    history = user_profile.get("reflection_history", [])
    variant = len(history) % 2
    template = REFLECTIONS[reflection_type][variant]

    if reflection_type == "connection":
        top_topic = user_profile.get("frequent_topics", ["this theme"])[0]
        return template.format(top_topic=top_topic)
    return template


def generate_reflection(user_profile: dict, user_message: str, ai_response: str) -> str:
    user_profile.setdefault("reflection_history", [])
    user_profile.setdefault("recent_topics", [])

    _remember_topics(user_profile, user_message)

    if user_profile.get("message_count", 0) % 3 != 0:
        return ""

    reflection_type = _select_reflection_type(user_profile, user_message, ai_response)
    reflection = _build_reflection(reflection_type, user_profile)
    _remember_reflection_type(user_profile, reflection_type)
    return reflection
