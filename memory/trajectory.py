from __future__ import annotations


SENTIMENT_ORDER = {
    "confused": 0,
    "uncertain": 1,
    "positive": 2,
    "insightful": 3,
}


def build_learning_trajectory(insights: list[dict]) -> dict | None:
    if len(insights) < 3:
        return None

    sentiments = [
        str(item.get("metadata", {}).get("sentiment", ""))
        for item in insights
    ]
    interpretations = [
        str(item.get("metadata", {}).get("interpretation", ""))
        for item in insights
    ]
    topics = [
        str(item.get("metadata", {}).get("topic", "this topic"))
        for item in insights
    ]
    topic = next((value for value in reversed(topics) if value), "this topic")

    if _is_progression(sentiments):
        guidance_options = [
            "You might explore how this understanding shows up in your own experiences now.",
            "It may help to notice where this pattern appears in your day-to-day life.",
            "You could try applying this insight to a real situation you're currently facing.",
        ]
        return {
            "trajectory_type": "progression",
            "summary": (
                f"Across your recent reflections, your understanding of {topic} "
                f"seems to be moving from uncertainty toward clearer insight."
            ),
            "guidance": guidance_options[len(insights) % len(guidance_options)],
        }

    if _is_refinement(interpretations):
        guidance_options = [
            "It could help to connect this understanding with related ideas you've been exploring.",
            "You might explore how this idea compares with other patterns you've noticed.",
            "You may want to see how this sharper understanding changes the way you read nearby concepts.",
        ]
        return {
            "trajectory_type": "refinement",
            "summary": (
                f"Your reflections on {topic} are becoming more specific and nuanced, "
                f"which suggests your understanding is sharpening over time."
            ),
            "guidance": guidance_options[len(insights) % len(guidance_options)],
        }

    if _is_stabilization(interpretations):
        guidance_options = [
            "You may want to consider gently testing this understanding from a new angle.",
            "It might help to question what this view leaves out or overlooks.",
            "You could explore whether this understanding still holds in a different context.",
        ]
        return {
            "trajectory_type": "stabilization",
            "summary": (
                f"A steady pattern is forming around {topic}: you keep returning to a similar "
                f"core insight, which suggests that understanding is becoming more stable."
            ),
            "guidance": guidance_options[len(insights) % len(guidance_options)],
        }

    return None


def _is_progression(sentiments: list[str]) -> bool:
    ordered = [SENTIMENT_ORDER.get(sentiment) for sentiment in sentiments if sentiment in SENTIMENT_ORDER]
    if len(ordered) < 3:
        return False
    return ordered == sorted(ordered) and ordered[-1] > ordered[0]


def _is_refinement(interpretations: list[str]) -> bool:
    lengths = [len(text.split()) for text in interpretations if text]
    if len(lengths) < 3:
        return False
    grows = lengths[-1] > lengths[0]
    keywords = [
        sum(1 for term in text.lower().split() if len(term) > 4)
        for text in interpretations
    ]
    return grows and keywords[-1] >= keywords[0]


def _is_stabilization(interpretations: list[str]) -> bool:
    normalized = [text.lower().strip() for text in interpretations if text]
    if len(normalized) < 3:
        return False
    recent = normalized[-3:]
    unique_recent = len(set(recent))
    return unique_recent <= 2
