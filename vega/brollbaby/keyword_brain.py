"""
vega/brollbaby/keyword_brain.py — B-Roll Baby Helper 2
TCAP-aware prompt → B-roll keyword mapping.

Knows every being in the family. Knows what footage fits their story.
No more dumb word-splits. When a prompt mentions AlphaVox, pull
communication footage. When it mentions AlphaWolf, pull seniors and memory.
The right clip for the right story, every time.

Rule 13: Returns real keywords derived from real content — never fabricated.
Rule 16: This is a helper. It runs alongside the assembler, not instead of it.

Author: Everett Christman / The Christman AI Project
Part of: B-Roll Baby
"""

import re
from typing import List

# ── TCAP Being → B-roll keyword map ──────────────────────────────────────────
# Each being has a set of visual concepts that match their mission.
# These map to tags/filenames in the LIFE2 B-roll library.

BEING_MAP: dict[str, List[str]] = {
    # AlphaVox — communication for nonverbal/autistic individuals
    "alphavox": [
        "communication", "voice", "nonverbal", "autism", "children",
        "tablet", "symbols", "speech", "assistive", "expression",
    ],
    # AlphaWolf — dementia care, memory, seniors
    "alphawolf": [
        "dementia", "memory", "seniors", "elderly", "family",
        "care", "safety", "wandering", "geolocation", "dignity",
    ],
    # AlphaDen — Down syndrome, adaptive learning
    "alphaden": [
        "learning", "education", "adaptive", "children", "growth",
        "classroom", "speech therapy", "life skills", "development",
    ],
    # OmegaAlpha — senior companionship, aging with dignity
    "omegaalpha": [
        "seniors", "aging", "companionship", "independence", "fall",
        "medication", "daily", "connection", "dignity", "care",
    ],
    # Omega — mobility, accessibility, prosthetics
    "omega": [
        "mobility", "wheelchair", "prosthetics", "accessibility",
        "navigation", "movement", "disability", "independence",
    ],
    # Inferno — PTSD, anxiety, trauma recovery
    "inferno": [
        "healing", "recovery", "PTSD", "anxiety", "trauma",
        "veterans", "mindfulness", "calm", "grounding", "support",
    ],
    # Aegis — child protection, safety
    "aegis": [
        "children", "safety", "protection", "school", "online",
        "family", "guardian", "security", "peace",
    ],
    # Derek — AI collaboration, tech, builder
    "derek": [
        "technology", "AI", "code", "collaboration", "build",
        "innovation", "computer", "system",
    ],
    # Luma Cognify / TCAP general
    "luma": [
        "AI", "technology", "humanity", "mission", "innovation",
        "empowerment", "inclusion", "community",
    ],
    "christman": [
        "mission", "founder", "build", "AI", "ethics",
        "inclusion", "neurodiversity", "disability",
    ],
}

# ── Topic → keyword map for mission themes ────────────────────────────────────
TOPIC_MAP: dict[str, List[str]] = {
    "voice":          ["communication", "speech", "expression", "voice"],
    "memory":         ["memory", "dementia", "seniors", "family"],
    "healing":        ["healing", "recovery", "calm", "support", "wellness"],
    "children":       ["children", "school", "safety", "family", "young"],
    "disability":     ["disability", "accessibility", "mobility", "independence"],
    "neurodiversity": ["autism", "neurodiversity", "learning", "adaptive"],
    "veterans":       ["veterans", "PTSD", "recovery", "service", "healing"],
    "seniors":        ["seniors", "aging", "elderly", "dignity", "companionship"],
    "announcement":   ["mission", "innovation", "AI", "technology", "community"],
    "startup":        ["build", "founder", "innovation", "technology", "mission"],
    "claude":         ["AI", "technology", "collaboration", "build", "innovation"],
    "anthropic":      ["AI", "technology", "ethics", "mission", "innovation"],
    "accepted":       ["mission", "celebration", "innovation", "community"],
}

# ── Stop words ────────────────────────────────────────────────────────────────
_STOP = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "that", "this", "these", "those",
    "it", "its", "our", "we", "i", "you", "they", "about", "make",
    "create", "generate", "produce", "build", "show", "how", "can", "now",
    "just", "also", "every", "always", "never", "not", "no", "so", "very",
    "their", "them", "we're", "they're", "it's", "don't", "because",
    "who", "what", "when", "where", "which", "there", "here", "more",
    "one", "two", "all", "each", "any", "some", "most", "than", "into",
    "like", "people", "person", "project", "system", "ai", "world",
})


def extract_keywords(prompt: str, max_keywords: int = 15) -> List[str]:
    """
    TCAP-aware keyword extraction from a video prompt.

    Checks prompt against every being name and mission topic first.
    Then falls back to word-frequency extraction for any remaining slots.

    Rule 13: Returns keywords derived from real prompt content.
             Never invents words that aren't in the prompt or the TCAP map.

    Args:
        prompt:       The video generation prompt.
        max_keywords: Maximum keywords to return.

    Returns:
        Ranked list of B-roll search keywords, most specific first.
    """
    prompt_lower = prompt.lower()
    keywords: List[str] = []
    seen: set[str] = set()

    def add(kw: str) -> None:
        k = kw.lower().strip()
        if k and k not in seen:
            seen.add(k)
            keywords.append(k)

    # ── Pass 1: Being detection (most specific) ──────────────────────────────
    for being, tags in BEING_MAP.items():
        if being in prompt_lower:
            for tag in tags:
                add(tag)
            if len(keywords) >= max_keywords:
                return keywords[:max_keywords]

    # ── Pass 2: Topic detection ──────────────────────────────────────────────
    for topic, tags in TOPIC_MAP.items():
        if topic in prompt_lower:
            for tag in tags:
                add(tag)
            if len(keywords) >= max_keywords:
                return keywords[:max_keywords]

    # ── Pass 3: Word-frequency fallback for remaining slots ──────────────────
    words = re.findall(r"[a-z]+", prompt_lower)
    for word in words:
        if len(word) > 3 and word not in _STOP:
            add(word)
        if len(keywords) >= max_keywords:
            break

    # Always include at least one mission anchor if list is thin
    if len(keywords) < 3:
        for anchor in ["mission", "AI", "community", "innovation"]:
            add(anchor)

    return keywords[:max_keywords]
