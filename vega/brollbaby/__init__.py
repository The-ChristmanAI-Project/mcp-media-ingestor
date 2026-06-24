"""
vega/brollbaby/ — B-Roll Baby
The collective helper group for Vega's video production pipeline.

We're famous now. We get it right. We get it tight.

Helpers:
    1. keyword_brain.py  — TCAP-aware prompt → B-roll tag mapping
    2. title_card.py     — FFmpeg branded TCAP title cards
    3. caption_style.py  — TCAP cyan branded caption overlay

Author: Everett Christman / The Christman AI Project
Named: B-Roll Baby — officially, permanently.
Cardinal Rules: All 16 apply.
"""

from .keyword_brain  import extract_keywords
from .title_card     import build_title_card
from .caption_style  import burn_captions

__all__ = ["extract_keywords", "build_title_card", "burn_captions"]
