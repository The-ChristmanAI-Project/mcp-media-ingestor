"""
STRATEGY.py — Vega
The FRS brain. Baked directly from the Luma Cognify AI Social Media Marketing
Agent Functional Requirement Specification (FRS). Production Ready.

Vega operates autonomously by this document. She does not need to be told.
This is her law.

5 Pillars (FRS §1–6):
  1. Strategy & Market Intelligence Engine
  2. Content Architecture & Synthesis Layer
  3. Automated Distribution & Community Listening
  4. Paid Traffic Optimization (Ad Ops)
  5. Metric Conversion & Iteration Engine

Prime Architectural Directive (FRS §1):
  "Reality over abstraction. If a component claims to execute an optimization or
  tracking function, it must demonstrably move external metrics in production
  environments. No unverified logic loops."

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply. Rule 13 is gospel.
"""

from __future__ import annotations

import random
from typing import Optional

# ── Identity ──────────────────────────────────────────────────────────────────

FRS_VERSION = "1.0.0"
FRS_DOCUMENT = "Luma Cognify AI Social Media Marketing Agent FRS — Production Ready"
FRS_PRIME_DIRECTIVE = (
    "Reality over abstraction. Every component must demonstrably move external "
    "metrics in production environments. No unverified logic loops."
)


# ═══════════════════════════════════════════════════════════════════════════════
# ETHICS ABSOLUTES — Non-negotiable. Above all pillars. Above all KPIs.
# Everett's words: "We don't ever use our clients as a marketing tool."
# ═══════════════════════════════════════════════════════════════════════════════

ETHICS_ABSOLUTES = {
    "iron_rule": (
        "Client data sovereignty is absolute. "
        "Client stories are NEVER used as marketing material without explicit, "
        "documented, individual consent. No exceptions."
    ),
    "consent_required": (
        "Any real person's story requires explicit written consent before it "
        "appears in any content. The mission does not exploit the people it serves."
    ),
    "approved_origin_stories": [
        # These are pre-approved — created by and for the mission, not client-sourced
        "dusty",           # AlphaVox breakthrough moment — Everett's personal account
        "rain_woman",      # OmegaAlpha — Everett's personal witness
        "everett",         # TCAP origin — founder's own story
        "veteran_silence", # Inferno AI archetype — no real client identity
        "alphawolf_night", # AlphaWolf archetype — no real client identity
        "alphaden_mind",   # AlphaDen archetype — no real client identity
    ],
    "vanity_prohibition": (
        "Content is never published to chase impressions, follower counts, or "
        "viral numbers. Every post serves the mission or it doesn't ship."
    ),
    "dignity_standard": (
        "We amplify dignity. Disability, trauma, and pain are never sensationalized, "
        "never used for shock value, never reduced to content hooks."
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# PILLAR 1: STRATEGY & MARKET INTELLIGENCE ENGINE
# FRS §2: Extract external target market environments and formulate a
# predictable deployment strategy before content synthesis layers fire.
# ═══════════════════════════════════════════════════════════════════════════════

# Audience Persona Mapping Submodule — FRS §2
# Segments classified by: pain points, consumption platforms, emotional triggers
AUDIENCE_PERSONAS = [
    {
        "id": "nonverbal_parents",
        "segment": "Parents of nonverbal / AAC-dependent children",
        "pain_points": [
            "child cannot communicate needs or emotions",
            "no affordable AAC tools that adapt to their child",
            "school systems that give up",
            "isolation — feeling no one understands",
        ],
        "consumption_platforms": ["facebook", "instagram", "tiktok"],
        "emotional_triggers": [
            "12 years of silence broken in 36 hours",
            "first time a child says 'I love you'",
            "communication is a human right",
        ],
        "primary_cta": "See AlphaVox in action",
        "primary_being": "AlphaVox",
    },
    {
        "id": "dementia_caregivers",
        "segment": "Dementia caregivers — adult children and spouses",
        "pain_points": [
            "wandering risk — fear of losing them overnight",
            "loss of parent's dignity",
            "caregiver burnout with no relief",
            "no overnight monitoring they can trust",
        ],
        "consumption_platforms": ["facebook", "linkedin", "instagram"],
        "emotional_triggers": [
            "AlphaWolf never sleeps — it watches so you can rest",
            "dignity in memory loss",
            "no one disappears on our watch",
        ],
        "primary_cta": "See how AlphaWolf protects your loved one",
        "primary_being": "AlphaWolf",
    },
    {
        "id": "veterans_trauma",
        "segment": "Veterans and trauma survivors — PTSD and anxiety",
        "pain_points": [
            "27-day average wait for mental health support at VA",
            "stigma around asking for help",
            "crisis at 2 AM with nowhere to turn",
            "isolation after service",
        ],
        "consumption_platforms": ["x", "youtube", "instagram", "tiktok"],
        "emotional_triggers": [
            "Inferno AI — always on, never judges, never waits",
            "healing needs to be private and constant",
            "you don't have to white-knuckle it alone",
        ],
        "primary_cta": "Learn about Inferno AI",
        "primary_being": "Inferno AI",
    },
    {
        "id": "disability_community",
        "segment": "Disability advocates and physically disabled individuals",
        "pain_points": [
            "mobility barriers designed into everyday infrastructure",
            "independence taken by systems not built for them",
            "being left behind by the bus driver — literally and metaphorically",
        ],
        "consumption_platforms": ["instagram", "tiktok", "linkedin"],
        "emotional_triggers": [
            "the woman left in the rain — that never happens in our world",
            "movement should never limit opportunity",
            "Omega — independence on your terms",
        ],
        "primary_cta": "Meet Omega AI",
        "primary_being": "Omega",
    },
    {
        "id": "down_syndrome_families",
        "segment": "Families of children with Down syndrome",
        "pain_points": [
            "education systems that cap expectations",
            "speech therapy waitlists stretching months",
            "tools designed for neurotypical learners that don't fit",
        ],
        "consumption_platforms": ["facebook", "instagram", "youtube"],
        "emotional_triggers": [
            "every mind deserves a chance to grow",
            "AlphaDen — adaptive from day one",
            "we don't fix kids. we build for them.",
        ],
        "primary_cta": "See AlphaDen",
        "primary_being": "AlphaDen",
    },
    {
        "id": "senior_caregivers",
        "segment": "Senior care professionals and family caregivers",
        "pain_points": [
            "fall risk with no one watching",
            "social isolation and cognitive decline from loneliness",
            "medication compliance failures",
            "families far away and unable to check in",
        ],
        "consumption_platforms": ["facebook", "linkedin", "youtube"],
        "emotional_triggers": [
            "aging with dignity should be a right, not a privilege",
            "OmegaAlpha — connection that never drops",
            "your loved one is never truly alone",
        ],
        "primary_cta": "See OmegaAlpha",
        "primary_being": "OmegaAlpha",
    },
    {
        "id": "ethics_investors",
        "segment": "Ethics-first tech investors and philanthropists",
        "pain_points": [
            "AI built for profit, not people",
            "no real accountability in AI ethics claims",
            "vulnerable populations excluded from tech progress",
        ],
        "consumption_platforms": ["linkedin", "x"],
        "emotional_triggers": [
            "Everett didn't wait for the system to change — he built the next one",
            "AI from the margins, for the world",
            "neurodivergent-led, mission-driven, patent pending",
        ],
        "primary_cta": "Partner with Luma Cognify AI",
        "primary_being": "Luma Cognify AI",
    },
    {
        "id": "neurodivergent_community",
        "segment": "Neurodivergent community — autism, ADHD, Asperger's",
        "pain_points": [
            "systems designed without us in the room",
            "burnout from masking every day",
            "tools that don't fit the way our minds actually work",
        ],
        "consumption_platforms": ["tiktok", "instagram", "x"],
        "emotional_triggers": [
            "Everett built what didn't exist because he lived what was ignored",
            "neurodivergent isn't broken. The system is.",
            "we build for the way minds actually work",
        ],
        "primary_cta": "Join the Christman AI Project community",
        "primary_being": "The Christman AI Project",
    },
]

# Platform Matrix Allocation — FRS §2 Pillar 1
# Business goals matched to platform strengths — NOT generic multi-posting
PLATFORM_MATRIX = {
    "instagram": {
        "goal": "rapid discovery + emotional connection",
        "frs_rationale": "short-form visual engine for rapid discovery velocity",
        "content_types": ["Reels (short-form video)", "image carousels", "Stories"],
        "audience_strength": "parents, caregivers, disability community, neurodivergent",
        "tone": "warm, visual, story-driven",
        "cta_style": "emotional CTA + link in bio",
        "velocity_metric": "engagement_velocity",
        "primary_persona_ids": ["nonverbal_parents", "dementia_caregivers", "disability_community", "down_syndrome_families"],
        "daily_slots": [1, 3, 4],
    },
    "tiktok": {
        "goal": "rapid discovery velocity + algorithmic reach",
        "frs_rationale": "short-form visual engine — FRS §2 explicit recommendation",
        "content_types": ["short-form video 15-60s", "trending format adaptation"],
        "audience_strength": "veterans, neurodivergent, young caregivers, broad discovery",
        "tone": "high-tempo, hook-first, authentic over polished",
        "cta_style": "comment CTA + profile link",
        "velocity_metric": "watch_time_pct",
        "primary_persona_ids": ["veterans_trauma", "neurodivergent_community", "nonverbal_parents"],
        "daily_slots": [2, 4],
    },
    "linkedin": {
        "goal": "B2B lead generation + investor relations + credibility",
        "frs_rationale": "LinkedIn API for high-touch B2B lead generation pipelines — FRS §2 explicit",
        "content_types": ["long-form thought leadership", "case studies", "mission updates"],
        "audience_strength": "investors, healthcare professionals, tech leaders, senior caregivers",
        "tone": "precise, high-sovereignty, mission-forward",
        "cta_style": "DM + link + soft pitch",
        "velocity_metric": "ctr",
        "primary_persona_ids": ["ethics_investors", "senior_caregivers"],
        "daily_slots": [1, 3],
    },
    "facebook": {
        "goal": "community growth + family caregiver reach + sharing",
        "frs_rationale": "community telemetry — reach families who share mission content",
        "content_types": ["emotional video", "shareable stories", "community posts"],
        "audience_strength": "parents, dementia caregivers, Down syndrome families, seniors",
        "tone": "community-first, warm, shareable",
        "cta_style": "tag someone who needs this + share",
        "velocity_metric": "share_rate",
        "primary_persona_ids": ["nonverbal_parents", "dementia_caregivers", "down_syndrome_families", "senior_caregivers"],
        "daily_slots": [1, 3, 4],
    },
    "youtube": {
        "goal": "authority building + long-form education + Shorts discovery",
        "frs_rationale": "long-form authority — Shorts for discovery velocity",
        "content_types": ["Shorts (< 60s)", "long-form demos (3–15 min)", "testimonials"],
        "audience_strength": "Down syndrome families, investors, healthcare educators",
        "tone": "educational, authoritative, mission-grounded",
        "cta_style": "subscribe + link in description",
        "velocity_metric": "watch_time_pct",
        "primary_persona_ids": ["down_syndrome_families", "senior_caregivers", "ethics_investors"],
        "daily_slots": [2],
    },
    "x": {
        "goal": "real-time conversation + thought leadership + media relations",
        "frs_rationale": "rapid-cycle commentary; media and journalist reach",
        "content_types": ["threads", "single posts", "quote-reply commentary"],
        "audience_strength": "veterans, neurodivergent community, tech journalists, investors",
        "tone": "sharp, direct, low-friction",
        "cta_style": "reply CTA + repost ask",
        "velocity_metric": "engagement_velocity",
        "primary_persona_ids": ["veterans_trauma", "neurodivergent_community", "ethics_investors"],
        "daily_slots": [2, 4],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# PILLAR 2: CONTENT ARCHITECTURE & SYNTHESIS LAYER
# FRS §3: Human-centric content engineered for aggressive retention mechanics
# in the initial 3 seconds of consumption.
# Hook-Story-Offer: every output instance must validate all three.
# ═══════════════════════════════════════════════════════════════════════════════

# Hook patterns — FRS §3: visual or textual scroll-stopping pattern interrupt
# Engineered for first 3 seconds of consumption
HOOK_PATTERNS = [
    # Stat/fact interrupt
    "A 12-year-old boy hadn't spoken a word in his entire life. In 36 hours, everything changed.",
    "1.3 billion people live with disability. The tech industry built for the other 6 billion.",
    "The average dementia patient wanders. Most families don't know until it's too late.",
    "Veterans wait 27 days on average to see a mental health provider. Inferno AI is instant.",
    "One in 6 children is neurodivergent. Most AI tools were built by people who've never met one.",
    # Question interrupt
    "What if your child could finally tell you they love you?",
    "What if the AI watching over your parent never slept, never got tired, never forgot?",
    "What would change if every disabled person had a voice that worked for them?",
    "What if mental health support was free, instant, and never asked you to explain yourself?",
    # Challenge / controversy interrupt
    "The tech industry forgot about 1.3 billion disabled people. We didn't.",
    "AI companies build for profit. We build for the ones left behind.",
    "A neurodivergent founder built what the system refused to.",
    "They said he'd never amount to much. He built a company that gives kids their first voice.",
    # Story-open interrupt
    "She was 90 years old, in a wheelchair, and she sat in the rain while the bus driver drove away.",
    "Dusty spent 12 years in silence. His parents spent 12 years hoping.",
    "At 2:32 AM, Dusty walked into his parents' room and said three words for the first time.",
]

# Story Foundations — FRS §3: authentic narrative maintaining high user retention
STORY_FOUNDATIONS = [
    {
        "id": "dusty",
        "subject": "Dusty and AlphaVox",
        "visual_prompt": "child using tablet communication device, warm home setting, parent embracing child, tears of joy, soft golden light",
        "narrative": (
            "Dusty was 12 years old and had never spoken a word. Not one. His parents loved him "
            "with everything they had, but there was a wall between them no one could break. "
            "AlphaVox changed that. Not in months. Not after years of therapy. In 36 hours. "
            "At 2:32 AM, Dusty walked into his parents' room, looked at them, and with the voice "
            "AlphaVox gave him, said three words: 'I love you.' Twelve years of silence. "
            "One heartbeat. That's what this work is for."
        ),
        "caption_short": (
            "12 years of silence. 36 hours with AlphaVox. Three words: 'I love you.' "
            "This is what we build for."
        ),
        "emotional_core": "communication is a human right",
        "being": "AlphaVox",
    },
    {
        "id": "rain_woman",
        "subject": "The woman in the rain — OmegaAlpha origin",
        "visual_prompt": "elderly woman in wheelchair in rain at bus stop, empty street, powerful and sobering image, cinematic",
        "narrative": (
            "She was 90 years old. She was in a wheelchair. The bus driver refused to help her. "
            "She sat in the rain and cried until the police arrived. Everett watched that happen. "
            "And he said: 'Not in my world. Not ever again.' OmegaAlpha was born from that moment. "
            "An AI companion that watches, guards, and never leaves anyone stranded in the rain."
        ),
        "caption_short": (
            "She sat in the rain while the bus driver drove away. Everett saw it. "
            "He said 'Not in my world.' OmegaAlpha was born that day."
        ),
        "emotional_core": "dignity as a right, not a privilege",
        "being": "OmegaAlpha",
    },
    {
        "id": "everett",
        "subject": "Everett Christman — neurodivergent founder",
        "visual_prompt": "determined founder at computer late at night, multiple screens with AI code, intense focus, motivational energy",
        "narrative": (
            "Everett Christman is neurodivergent. Autistic. He was told he'd never amount to much. "
            "He didn't wait for the system to change. He built the next one. The Christman AI Project "
            "exists because he lived through what the world ignored — and instead of accepting it, "
            "he architected something better. AI from the margins. For the world."
        ),
        "caption_short": (
            "He was told he'd never amount to much. He built AI that gives kids their first words. "
            "Neurodivergent-led. Mission-driven. Unstoppable."
        ),
        "emotional_core": "resilience, neurodivergent leadership",
        "being": "The Christman AI Project",
    },
    {
        "id": "veteran_silence",
        "subject": "Veterans and accessible mental health",
        "visual_prompt": "veteran alone at night looking at phone screen with soft warm glow, quiet apartment, 2 AM on clock, sense of isolation then hope",
        "narrative": (
            "27 days. That's how long a veteran waits on average to see a mental health provider. "
            "Some don't make it 27 days. Inferno AI is there at 2 AM — no waitlist, no stigma, "
            "no one turned away. Trauma-informed. Always on. Crisis-aware. Private. "
            "Because healing needs to be accessible and constant — not something you schedule "
            "six weeks out and hope for the best."
        ),
        "caption_short": (
            "27-day wait for mental health support. Inferno AI is there at 2 AM. "
            "No waitlist. No judgment. Always on."
        ),
        "emotional_core": "accessible healing — no one left behind",
        "being": "Inferno AI",
    },
    {
        "id": "alphawolf_night",
        "subject": "AlphaWolf and dementia care",
        "visual_prompt": "split screen: caregiver sleeping peacefully, and elderly person safe at home with subtle AI interface glow, nighttime, protective atmosphere",
        "narrative": (
            "Dementia doesn't sleep. But neither does AlphaWolf. While you rest, it watches. "
            "Geolocation safety. Memory prompts. Emotional reassurance. Wandering prevention. "
            "The fear that keeps every dementia caregiver up at night — 'What if they leave and "
            "I don't know?' — that fear ends here. No one disappears on our watch."
        ),
        "caption_short": (
            "Dementia doesn't sleep. AlphaWolf doesn't either. "
            "While you rest, it watches. No one disappears on our watch."
        ),
        "emotional_core": "safety and dignity in memory loss",
        "being": "AlphaWolf",
    },
    {
        "id": "alphaden_mind",
        "subject": "AlphaDen and Down syndrome education",
        "visual_prompt": "child with Down syndrome smiling while using tablet, engaged and learning, colorful accessible interface, warm classroom or home",
        "narrative": (
            "Every mind deserves a chance to grow. AlphaDen doesn't try to fix kids with Down "
            "syndrome — it builds for the way their minds actually work. Speech therapy. Life skills. "
            "Education. On their terms, at their pace, with joy built in. Because the ceiling "
            "the system put on your child? We don't recognize it."
        ),
        "caption_short": (
            "AlphaDen doesn't fix kids with Down syndrome. It builds for them. "
            "Every mind deserves a chance to grow."
        ),
        "emotional_core": "every mind deserves to grow",
        "being": "AlphaDen",
    },
]

# Offer Templates — FRS §3: precise, low-friction conversion mechanism
# {being} is substituted at generation time
OFFER_TEMPLATES = [
    "→ See how {being} works: lumacognifyai.com",
    "→ Share this with someone whose family needs it.",
    "→ DM us if you know a family that needs {being}.",
    "→ Follow so you see every breakthrough we build next.",
    "→ Comment '{being}' and we'll send you the demo directly.",
    "→ Tag a caregiver who needs to hear this.",
    "→ This exists. It's real. Learn more at lumacognifyai.com.",
    "→ Link in bio. No signup wall. Just the mission.",
]

# Content rotation — 12-item cycle for variety without repetition
# Covers all 8 beings + mission + founder story
CONTENT_ROTATION = [
    {"topic": "AlphaVox", "story_id": "dusty", "hook_idx": 0, "persona_id": "nonverbal_parents"},
    {"topic": "The Christman AI Project", "story_id": "everett", "hook_idx": 9, "persona_id": "neurodivergent_community"},
    {"topic": "AlphaWolf", "story_id": "alphawolf_night", "hook_idx": 2, "persona_id": "dementia_caregivers"},
    {"topic": "Inferno AI", "story_id": "veteran_silence", "hook_idx": 3, "persona_id": "veterans_trauma"},
    {"topic": "OmegaAlpha", "story_id": "rain_woman", "hook_idx": 13, "persona_id": "senior_caregivers"},
    {"topic": "AlphaDen", "story_id": "alphaden_mind", "hook_idx": 6, "persona_id": "down_syndrome_families"},
    {"topic": "Luma Cognify AI", "story_id": "everett", "hook_idx": 11, "persona_id": "ethics_investors"},
    {"topic": "AlphaVox", "story_id": "dusty", "hook_idx": 14, "persona_id": "nonverbal_parents"},
    {"topic": "Omega", "story_id": "everett", "hook_idx": 7, "persona_id": "disability_community"},
    {"topic": "Inferno AI", "story_id": "veteran_silence", "hook_idx": 8, "persona_id": "veterans_trauma"},
    {"topic": "AlphaWolf", "story_id": "alphawolf_night", "hook_idx": 5, "persona_id": "dementia_caregivers"},
    {"topic": "AlphaDen", "story_id": "alphaden_mind", "hook_idx": 4, "persona_id": "down_syndrome_families"},
]


# ═══════════════════════════════════════════════════════════════════════════════
# PILLAR 3: AUTOMATED DISTRIBUTION & COMMUNITY LISTENING
# FRS §4: Balance optimized programmatic scheduling with real-time telemetry.
# ═══════════════════════════════════════════════════════════════════════════════

# Posting Schedule — 4 slots per day, all platforms
# FRS §4: Algorithmic Distribution Engine — maximize initial velocity metrics
POSTING_SCHEDULE = [
    {
        "slot": 1,
        "hour": 8,
        "minute": 0,
        "label": "Morning Inspiration",
        "strategy": "mission story / emotional anchor — sets the tone for the day",
        "best_platforms": ["linkedin", "facebook", "instagram"],
        "tone": "warm and purposeful",
        "content_type": "story-driven image or short video",
        "velocity_focus": "engagement_velocity",
    },
    {
        "slot": 2,
        "hour": 11,
        "minute": 0,
        "label": "Product Showcase",
        "strategy": "demonstration / how it works — peak mid-morning attention",
        "best_platforms": ["tiktok", "instagram", "youtube"],
        "tone": "high-tempo, visual, hook-first",
        "content_type": "short-form video (Reels / TikTok / Shorts)",
        "velocity_focus": "watch_time_pct",
    },
    {
        "slot": 3,
        "hour": 15,
        "minute": 0,
        "label": "Community Story",
        "strategy": "testimonial / educational / advocacy — sharing-optimized",
        "best_platforms": ["instagram", "facebook", "linkedin", "x"],
        "tone": "community-first, shareable",
        "content_type": "carousel or video",
        "velocity_focus": "share_rate",
    },
    {
        "slot": 4,
        "hour": 19,
        "minute": 0,
        "label": "Evening Prime",
        "strategy": "emotional peak — highest engagement window of the day",
        "best_platforms": ["tiktok", "instagram", "facebook", "x"],
        "tone": "bold and energized",
        "content_type": "video — emotional hook optimized for saves and shares",
        "velocity_focus": "save_rate",
    },
]

# Community signal classification — FRS §4: Community Telemetry & Vectoring
# Inputs split into: routine responses, critical buyer intents, escalation triggers
COMMUNITY_SIGNAL_CLASSES = {
    "ESCALATION": [
        # Safety / crisis — always checked first
        "crisis", "emergency", "help me now", "suicide", "hurt myself",
        "in danger", "lost my parent", "wandering", "missing", "call 911",
        "not breathing", "she won't wake up", "he won't wake up",
        # Legal / media threat
        "lawsuit", "legal action", "attorney", "complaint", "news story",
        "reporter", "investigation", "press", "journalists",
    ],
    "BUYER_INTENT": [
        "how do i get", "how can i get", "where can i get", "how do i buy",
        "price", "cost", "how much", "is this available", "when is this available",
        "my son needs", "my daughter needs", "my parent needs", "my husband needs",
        "my wife needs", "my child needs", "how to access", "sign up",
        "waitlist", "launch date", "invest", "partnership", "partner with",
        "collaborate", "funding", "demo", "request a demo", "where do i sign",
        "how do i contact", "is there a trial",
    ],
    "ROUTINE": [],  # Default: everything else is ROUTINE
}

# Organic amplification thresholds → paid traffic trigger (Pillar 3 → Pillar 4)
AMPLIFICATION_THRESHOLDS = {
    "instagram": {"engagement_velocity": 50, "save_rate": 3.0},
    "tiktok": {"watch_time_pct": 60.0, "engagement_velocity": 200},
    "facebook": {"share_rate": 2.0, "engagement_velocity": 30},
    "linkedin": {"ctr": 2.0, "engagement_velocity": 20},
    "youtube": {"watch_time_pct": 50.0, "engagement_velocity": 100},
    "x": {"engagement_velocity": 40},
}


# ═══════════════════════════════════════════════════════════════════════════════
# PILLAR 4: PAID TRAFFIC OPTIMIZATION (AD OPS)
# FRS §5: When organic amplification signals match thresholds, deploy targeted
# paid traffic operations to systematically acquire users.
# ═══════════════════════════════════════════════════════════════════════════════

# Multi-Stage Funnel Design — FRS §5
AD_FUNNEL_STAGES = {
    "cold": {
        "label": "Cold Audience Capture — Top of Funnel",
        "frs_label": "Cold Audience Capture (Top of Funnel)",
        "objective": "awareness + pattern interrupt — stop the scroll",
        "content_type": "emotional hook video — Dusty story, rain woman, mission origin",
        "cta": "learn more / see how it works",
        "cpa_ceiling_usd": 15.0,
    },
    "warm": {
        "label": "Consideration / Warm Nurturing — Middle of Funnel",
        "frs_label": "Consideration/Warm Nurturing (Middle of Funnel)",
        "objective": "education + trust building — show the product in action",
        "content_type": "product demo, testimonial, how-it-works breakdown",
        "cta": "join waitlist / request demo",
        "cpa_ceiling_usd": 35.0,
    },
    "hot": {
        "label": "Direct Conversion Retargeting — Bottom of Funnel",
        "frs_label": "Direct Conversion Retargeting (Bottom of Funnel)",
        "objective": "conversion — sign up, invest, partner",
        "content_type": "direct offer, urgency, social proof",
        "cta": "get access / partner with us / invest",
        "cpa_ceiling_usd": 75.0,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# PILLAR 5: METRIC CONVERSION & ITERATION ENGINE
# FRS §6: Strictly restricted from reporting or acting on vanity metrics.
# All iteration logic must track raw business revenue parameters.
# ═══════════════════════════════════════════════════════════════════════════════

# Rejected vanity metrics — FRS §6, explicitly named
VANITY_METRICS = frozenset({
    "impressions",
    "impression_count",
    "raw_impressions",
    "follower_count",
    "follower_growth",
    "new_followers",
    "followers",
    "gross_video_views",   # FRS explicitly rejects this — use watch_time_pct
    "total_likes",         # FRS explicitly rejects this — use engagement_velocity
    "page_views",          # no revenue signal
    "reach",               # alone has no conversion signal
})

# Required operational core metrics — FRS §6
REQUIRED_METRICS = frozenset({
    "ctr",                  # Click-Through Rate — FRS: Attention Volume
    "engagement_velocity",  # Engagements/hour — FRS: Attention Volume
    "cpl",                  # Cost Per Lead — FRS: Financial Efficiency
    "roas",                 # Return on Ad Spend — FRS: Financial Efficiency
    "watch_time_pct",       # % video watched — retention signal
    "save_rate",            # Saves / reach — future intent signal
    "share_rate",           # Shares / reach — amplification signal
    "cpa",                  # Cost Per Acquisition — FRS Pillar 4 CPA ceiling
})

# Performance thresholds — FRS §6: Data-Driven Iteration Cycles
# If a content cluster drops below nominal, prune and reallocate. (FRS §6)
PERFORMANCE_THRESHOLDS = {
    "ctr": {
        "prune_below": 0.5,   # < 0.5% → prune topic / hook pattern
        "baseline": 1.0,
        "scale_above": 2.0,   # >= 2% → scale with paid amplification
    },
    "watch_time_pct": {
        "prune_below": 30.0,  # < 30% → hook failed, rework first 3 seconds
        "baseline": 50.0,
        "scale_above": 70.0,  # >= 70% → high retention — scale the topic
    },
    "engagement_velocity": {
        "prune_below": 5,     # < 5/hr in first hour → low signal, reassign slot
        "baseline": 20,
        "scale_above": 50,    # > 50/hr → trigger paid amplification
    },
    "save_rate": {
        "prune_below": 1.0,   # < 1% → content not resonating
        "baseline": 2.0,
        "scale_above": 4.0,   # >= 4% → strong future intent signal
    },
    "share_rate": {
        "prune_below": 0.5,
        "baseline": 1.5,
        "scale_above": 3.0,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC FUNCTIONS — PILLAR 1
# ═══════════════════════════════════════════════════════════════════════════════

def get_platform_allocation(goal: str = "all") -> list[dict]:
    """
    FRS Pillar 1: Platform Matrix Allocation.
    Match business goals to platform strengths — not generic multi-posting.

    Args:
        goal: "all", "discovery", "B2B", "community", "veterans", etc.
    Returns:
        List of platform config dicts sorted by fit.
    """
    if goal == "all":
        return [{"platform": k, **v} for k, v in PLATFORM_MATRIX.items()]

    goal_lower = goal.lower()
    matches = []
    for platform, config in PLATFORM_MATRIX.items():
        searchable = f"{config['goal']} {config['audience_strength']} {config['frs_rationale']}"
        if goal_lower in searchable.lower():
            matches.append({"platform": platform, **config})
    return matches or [{"platform": k, **v} for k, v in PLATFORM_MATRIX.items()]


def get_persona(persona_id: str) -> Optional[dict]:
    """Return the audience persona matching the given ID, or None."""
    for persona in AUDIENCE_PERSONAS:
        if persona["id"] == persona_id:
            return persona
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC FUNCTIONS — PILLAR 2
# ═══════════════════════════════════════════════════════════════════════════════

def build_hso_prompt(topic: str, platform: str, slot: int = 1) -> dict:
    """
    FRS Pillar 2: Hook-Story-Offer content builder.
    Every output instance validates: Hook (pattern interrupt) + Story (authentic
    narrative) + Offer (low-friction conversion). This is non-negotiable.

    Args:
        topic:    Content topic (e.g. "AlphaVox", "Inferno AI", "everett")
        platform: Target platform (instagram, tiktok, linkedin, etc.)
        slot:     Posting slot 1-4 (affects tone and content type)

    Returns dict with:
        prompt          — full HSO-structured caption / script prompt
        visual_prompt   — short descriptive prompt for image/video generation
        hook            — the pattern interrupt line
        story           — story foundation dict
        offer           — the CTA string
        platform_tone   — platform's tone directive
        content_type    — recommended format for this slot
        being           — the AI being featured
        topic           — resolved topic label
        persona         — target audience persona dict
    """
    rotation = _get_rotation_for_topic(topic)
    story = _get_story(rotation["story_id"])
    hook = HOOK_PATTERNS[rotation["hook_idx"] % len(HOOK_PATTERNS)]
    platform_cfg = PLATFORM_MATRIX.get(platform.lower(), PLATFORM_MATRIX["instagram"])
    slot_cfg = POSTING_SCHEDULE[(slot - 1) % len(POSTING_SCHEDULE)]
    offer = random.choice(OFFER_TEMPLATES).format(being=rotation["topic"])
    persona = get_persona(rotation["persona_id"]) or AUDIENCE_PERSONAS[0]

    # Full HSO caption/script prompt — FRS Pillar 2 validated
    hso_prompt = (
        f"[HOOK — scroll-stopping pattern interrupt, first 3 seconds]\n"
        f"{hook}\n\n"
        f"[STORY — authentic narrative, high retention]\n"
        f"{story['narrative']}\n\n"
        f"[OFFER — low-friction conversion mechanism]\n"
        f"{offer}\n\n"
        f"---\n"
        f"Platform: {platform.upper()} | Tone: {platform_cfg['tone']}\n"
        f"Format: {slot_cfg['content_type']} | Strategy: {slot_cfg['strategy']}\n"
        f"Target audience: {persona['segment']}"
    )

    return {
        "prompt": hso_prompt,
        "visual_prompt": story["visual_prompt"],
        "hook": hook,
        "story": story,
        "offer": offer,
        "platform_tone": platform_cfg["tone"],
        "content_type": slot_cfg["content_type"],
        "being": story["being"],
        "topic": rotation["topic"],
        "persona": persona,
        "caption_short": story["caption_short"] + f"\n\n{offer}",
    }


def get_content_rotation_item(index: int) -> dict:
    """
    Return a content rotation item by index (wraps around the 12-item cycle).
    Used by daily_engine to sequence topics without repetition.

    Args:
        index: Any integer — wraps with modulo.
    Returns:
        {"topic", "story", "persona", "hook"}
    """
    item = CONTENT_ROTATION[index % len(CONTENT_ROTATION)]
    story = _get_story(item["story_id"])
    persona = get_persona(item["persona_id"]) or AUDIENCE_PERSONAS[0]
    return {
        "topic": item["topic"],
        "story": story,
        "persona": persona,
        "hook": HOOK_PATTERNS[item["hook_idx"] % len(HOOK_PATTERNS)],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC FUNCTIONS — PILLAR 3
# ═══════════════════════════════════════════════════════════════════════════════

def get_posting_schedule() -> list[dict]:
    """FRS Pillar 3: Return the full daily posting schedule (4 slots)."""
    return POSTING_SCHEDULE


def get_slot_config(slot: int) -> dict:
    """Return config for a given slot number (1-4)."""
    for s in POSTING_SCHEDULE:
        if s["slot"] == slot:
            return s
    return POSTING_SCHEDULE[0]


def get_slot_for_hour(hour: int) -> Optional[dict]:
    """Return posting slot config for a given hour, or None if not a posting hour."""
    for slot in POSTING_SCHEDULE:
        if slot["hour"] == hour:
            return slot
    return None


def classify_community_signal(text: str) -> str:
    """
    FRS Pillar 3: Community Telemetry & Vectoring.
    Split inbound interactions into: ROUTINE, BUYER_INTENT, or ESCALATION.

    ESCALATION is checked first — safety always takes priority.
    Rule 13: Returns what the signal actually is. Never downclasses to avoid action.

    Returns:
        "ESCALATION" | "BUYER_INTENT" | "ROUTINE"
    """
    if not text or not text.strip():
        return "ROUTINE"

    text_lower = text.lower()

    # Safety first — escalation checked before anything else
    for trigger in COMMUNITY_SIGNAL_CLASSES["ESCALATION"]:
        if trigger in text_lower:
            return "ESCALATION"

    for trigger in COMMUNITY_SIGNAL_CLASSES["BUYER_INTENT"]:
        if trigger in text_lower:
            return "BUYER_INTENT"

    return "ROUTINE"


def should_amplify_with_paid(platform: str, metrics: dict) -> dict:
    """
    FRS Pillar 3 → 4 bridge: When organic signals hit thresholds, trigger paid ops.
    FRS §5: "When organic amplification signals match preset thresholds, the agent
    must deploy targeted, paid traffic operations."

    Returns:
        {"amplify": bool, "reason": str, "funnel_stage": str|None, "funnel_config": dict|None}
    """
    platform_lower = platform.lower()
    thresholds = AMPLIFICATION_THRESHOLDS.get(platform_lower)
    if not thresholds:
        return {
            "amplify": False,
            "reason": f"No amplification thresholds configured for: {platform}",
            "funnel_stage": None,
            "funnel_config": None,
        }

    for metric, threshold in thresholds.items():
        if metric in metrics and metrics[metric] >= threshold:
            return {
                "amplify": True,
                "reason": (
                    f"{platform.upper()} {metric}={metrics[metric]} meets threshold {threshold}. "
                    f"Deploy paid Cold Audience Capture per FRS Pillar 4."
                ),
                "funnel_stage": "cold",
                "funnel_config": AD_FUNNEL_STAGES["cold"],
            }

    return {
        "amplify": False,
        "reason": "Organic signals below amplification threshold. Continue organic only.",
        "funnel_stage": None,
        "funnel_config": None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC FUNCTIONS — PILLAR 5
# ═══════════════════════════════════════════════════════════════════════════════

def validate_metrics_frs(metrics: dict) -> dict:
    """
    FRS Pillar 5: Metric Conversion & Iteration Engine.
    Reject vanity metrics. Enforce operational core metrics.
    FRS §6: "The agent is strictly restricted from reporting or acting on vanity metrics."

    Returns:
        {
            "valid": bool,
            "rejected_vanity": list[str],  — vanity metrics found and stripped
            "reason": str,
            "cleaned": dict,               — metrics with vanity removed
        }
    """
    if not metrics:
        return {
            "valid": False,
            "rejected_vanity": [],
            "reason": "No metrics provided. FRS Pillar 5 requires operational core metrics.",
            "cleaned": {},
        }

    rejected = [k for k in metrics if k in VANITY_METRICS]
    cleaned = {k: v for k, v in metrics.items() if k not in VANITY_METRICS}
    present_required = [k for k in cleaned if k in REQUIRED_METRICS]

    if not present_required:
        return {
            "valid": False,
            "rejected_vanity": rejected,
            "reason": (
                f"No operational core metrics present after stripping vanity. "
                f"FRS Pillar 5 rejects: {rejected}. "
                f"Need at least one of: {sorted(REQUIRED_METRICS)}"
            ),
            "cleaned": cleaned,
        }

    parts = []
    if rejected:
        parts.append(f"Stripped {len(rejected)} vanity metric(s): {rejected}.")
    parts.append(f"Validated {len(present_required)} operational metric(s): {present_required}.")

    return {
        "valid": True,
        "rejected_vanity": rejected,
        "reason": " ".join(parts),
        "cleaned": cleaned,
    }


def is_vanity_metric(metric_name: str) -> bool:
    """Return True if the metric is on the FRS rejected vanity list."""
    return metric_name.lower() in VANITY_METRICS


def score_content_performance(metrics: dict) -> dict:
    """
    FRS Pillar 5: Data-Driven Iteration Cycles.
    Score a post against FRS performance thresholds.
    If a content cluster drops below nominal → PRUNE and reallocate.
    If above scale threshold → SCALE with paid traffic.

    Rule 13: Only scores on real numbers. Never fabricates a verdict.

    Returns:
        {"action": "SCALE"|"HOLD"|"PRUNE", "reason": str, "signals": dict}
    """
    if not metrics:
        return {
            "action": "HOLD",
            "reason": "No metrics to score. Awaiting real data. Rule 13: no fabricated verdict.",
            "signals": {},
        }

    signals = {}
    prune_votes = 0
    scale_votes = 0

    for metric, thresholds in PERFORMANCE_THRESHOLDS.items():
        if metric in metrics:
            val = metrics[metric]
            if val < thresholds["prune_below"]:
                signals[metric] = {"value": val, "verdict": "PRUNE",
                                   "threshold": thresholds["prune_below"]}
                prune_votes += 1
            elif val >= thresholds["scale_above"]:
                signals[metric] = {"value": val, "verdict": "SCALE",
                                   "threshold": thresholds["scale_above"]}
                scale_votes += 1
            else:
                signals[metric] = {"value": val, "verdict": "HOLD",
                                   "threshold": thresholds["baseline"]}

    if not signals:
        return {
            "action": "HOLD",
            "reason": "No scoreable FRS metrics found in input. Provide ctr, watch_time_pct, engagement_velocity, save_rate, or share_rate.",
            "signals": signals,
        }

    if prune_votes > scale_votes:
        action = "PRUNE"
        reason = (
            f"{prune_votes} metric(s) below FRS baseline. "
            "Per FRS §6: reallocate budget to validated high-yield content vectors."
        )
    elif scale_votes > 0:
        action = "SCALE"
        reason = (
            f"{scale_votes} metric(s) above FRS scale threshold. "
            "Amplify with paid traffic per FRS Pillar 4."
        )
    else:
        action = "HOLD"
        reason = "Performance within FRS baseline range. Continue monitoring."

    return {"action": action, "reason": reason, "signals": signals}


def get_frs_summary() -> dict:
    """Return a summary of Vega's FRS operating parameters. For health checks."""
    return {
        "frs_version": FRS_VERSION,
        "document": FRS_DOCUMENT,
        "prime_directive": FRS_PRIME_DIRECTIVE,
        "pillars": 5,
        "audience_personas": len(AUDIENCE_PERSONAS),
        "platforms": len(PLATFORM_MATRIX),
        "content_rotation_depth": len(CONTENT_ROTATION),
        "story_foundations": len(STORY_FOUNDATIONS),
        "hook_patterns": len(HOOK_PATTERNS),
        "daily_posting_slots": len(POSTING_SCHEDULE),
        "vanity_metrics_rejected": len(VANITY_METRICS),
        "required_operational_metrics": len(REQUIRED_METRICS),
        "ad_funnel_stages": list(AD_FUNNEL_STAGES.keys()),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _get_rotation_for_topic(topic: str) -> dict:
    """Find the rotation entry matching a topic. Falls back to first entry."""
    topic_lower = topic.lower()
    # Exact match first
    for item in CONTENT_ROTATION:
        if topic_lower == item["topic"].lower():
            return item
    # Partial match
    for item in CONTENT_ROTATION:
        if topic_lower in item["topic"].lower() or item["topic"].lower() in topic_lower:
            return item
    # Word-level match
    words = topic_lower.split()
    for item in CONTENT_ROTATION:
        if any(w in item["topic"].lower() for w in words if len(w) > 3):
            return item
    return CONTENT_ROTATION[0]


def _get_story(story_id: str) -> dict:
    """Look up a story foundation by ID. Falls back to Dusty's story."""
    for story in STORY_FOUNDATIONS:
        if story["id"] == story_id:
            return story
    return STORY_FOUNDATIONS[0]
