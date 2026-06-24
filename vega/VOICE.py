"""
VOICE.py — Vega
Tone engine, caption generation, content copy writer.
Vega's voice is confident, warm, bold, and data-grounded.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply. Rule 13 is gospel.
"""

import logging
from typing import Optional
from .SOUL import TONE_DEFAULT, TONE_CELEBRATION, TONE_ANALYTICAL, get_platform_config

logger = logging.getLogger("vega.voice")

# Caption templates per platform tone
CAPTION_HOOKS = {
    "mission": [
        "We didn't wait for the world to change. We built the next one.",
        "From the margins, for the world. This is what AI built with love looks like.",
        "Every line of code carries a story. Every story carries a purpose.",
        "Building AI that doesn't just work — it feels, it remembers, it cares.",
    ],
    "product": [
        "This isn't a tool. It's a conversation. It's {being_name}.",
        "No internet? No problem. No power for five days? Still running.",
        "{being_name} adapts to the person. Not the other way around.",
    ],
    "story": [
        "12 years of silence ended at 2:32 AM with three words: 'I love you.'",
        "He didn't wait for the system to change. He built the next one.",
        "Dignity is not a feature. It's the foundation.",
    ],
    "cta": [
        "Follow to see what AI built from the heart looks like.",
        "Share if you believe tech should serve people first.",
        "Link in bio. The work is real. The mission is alive.",
    ],
}

# Platform-specific hashtag sets
HASHTAG_SETS = {
    "mission": [
        "#ChristmanAIProject", "#LumaCognifyAI", "#AIForGood",
        "#NeurodivergentLed", "#EthicalAI", "#TechWithPurpose",
    ],
    "alphavox": [
        "#AlphaVox", "#AAC", "#NonverbalCommunication",
        "#AutismTech", "#CommunicationIsAHumanRight",
    ],
    "alphawolf": [
        "#AlphaWolf", "#DementiaCare", "#AgingWithDignity",
        "#CaregiverSupport", "#MemoryTech",
    ],
    "inferno": [
        "#InfernoAI", "#PTSDRecovery", "#MentalHealthTech",
        "#TraumaInformed", "#HealingAccessible",
    ],
    "aegis": [
        "#AegisAI", "#ChildSafety", "#ChildProtection",
        "#OnlineSafety", "#ProtectOurChildren",
    ],
    "general": [
        "#AI", "#Innovation", "#Accessibility",
        "#NeurodivergentStrong", "#TechForAll",
    ],
}


def write_caption(
    prompt: str,
    platform: str,
    topic: str = "mission",
    include_cta: bool = True,
    tone: str = TONE_DEFAULT,
) -> dict:
    """
    Generate a caption for a post.

    This is a structured template engine — it does NOT call an LLM directly.
    LLM-enhanced captions go through the bridge broadcast to all beings.

    Returns:
        {
            "caption": str,
            "hashtags": list,
            "char_count": int,
            "platform": str,
            "within_limit": bool
        }
    """
    config = get_platform_config(platform)
    max_chars = config["max_caption_chars"]

    # Build caption from prompt + hook + CTA
    hook = CAPTION_HOOKS.get(topic, CAPTION_HOOKS["mission"])[0]
    hashtags = HASHTAG_SETS.get(topic, HASHTAG_SETS["general"])

    cta_line = ""
    if include_cta:
        cta = CAPTION_HOOKS["cta"][0]
        cta_line = f"\n\n{cta}"

    hashtag_str = " ".join(hashtags)

    # For X (Twitter), keep it tight
    if platform.lower() == "x":
        caption = f"{prompt[:200]}\n\n{hashtag_str}"
    else:
        caption = f"{prompt}\n\n{hook}{cta_line}\n\n{hashtag_str}"

    char_count = len(caption)
    within_limit = char_count <= max_chars

    if not within_limit:
        logger.warning(
            f"[Vega.Voice] Caption for {platform} is {char_count} chars "
            f"(limit: {max_chars}). Truncating."
        )
        caption = caption[:max_chars - 3] + "..."
        char_count = len(caption)
        within_limit = True

    return {
        "caption": caption,
        "hashtags": hashtags,
        "char_count": char_count,
        "platform": platform,
        "within_limit": within_limit,
        "tone": tone,
    }


def format_analytics_copy(metrics: dict, platform: str) -> str:
    """
    Format analytics data into human-readable copy for reports.
    Rule 13: Only describes real metrics — never invents numbers.
    """
    views = metrics.get("views", 0)
    likes = metrics.get("likes", 0)
    comments = metrics.get("comments", 0)
    shares = metrics.get("shares", 0)
    reach = metrics.get("reach", 0)

    lines = [
        f"📊 {platform.upper()} PERFORMANCE",
        f"Views / Plays: {views:,}",
        f"Likes: {likes:,}",
        f"Comments: {comments:,}",
        f"Shares / Reposts: {shares:,}",
    ]
    if reach:
        lines.append(f"Reach: {reach:,}")

    engagement_rate = (
        ((likes + comments + shares) / views * 100) if views > 0 else 0
    )
    lines.append(f"Engagement Rate: {engagement_rate:.2f}%")

    return "\n".join(lines)


def get_tone_register(context: str) -> str:
    """
    Return the appropriate tone register based on context.
    Honest function — returns a string constant, never fabricates.
    """
    context_lower = context.lower()
    if any(word in context_lower for word in ["crisis", "emergency", "urgent", "critical"]):
        return "calm_and_direct"
    if any(word in context_lower for word in ["win", "launch", "milestone", "success"]):
        return TONE_CELEBRATION
    if any(word in context_lower for word in ["report", "analytics", "metrics", "data"]):
        return TONE_ANALYTICAL
    return TONE_DEFAULT
