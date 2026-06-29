"""
daily_engine.py — vega
Daily content engine. Every day at scheduled times, generates 4 social media
posts across all platforms and alerts Everett that they're ready to post.

Schedule (local time):
    08:00 — Slot 1: Morning Inspiration
    11:00 — Slot 2: Product Showcase
    15:00 — Slot 3: Community Story
    19:00 — Slot 4: Evening Prime

FRS Compliance (Luma Cognify AI Social Media Marketing Agent FRS):
    - Content rotates through 12-item mission-driven sequence (Pillar 2)
    - Every post is Hook-Story-Offer structured (Pillar 2)
    - Slots are platform-optimized per FRS matrix (Pillar 1)
    - Captions carry the HSO framework, not random topics (Pillar 2)
    Vega knows what to post. She does not need to be told.

Rule 1: Jobs must actually fire and actually generate content.
Rule 6: Every failure surfaces immediately — logged and alerted.
Rule 13: Never marks content "ready" unless it was actually generated.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply.
"""

from __future__ import annotations

import logging
import os
import random
import sys
from datetime import datetime
from typing import Optional

logger = logging.getLogger("vega.daily_engine")

ALL_PLATFORMS = ["instagram", "tiktok", "linkedin", "facebook", "x", "clapper"]


# ── FRS Content Rotation ───────────────────────────────────────────────────────

def _get_rotation_index(slot: int) -> int:
    """
    Derive content rotation index from current day + slot number.
    Ensures different topics each day and no same topic repeating across slots.
    Day-of-year (1-365) * 4 + slot → wraps over the 12-item rotation cycle.
    """
    day_of_year = int(datetime.now().strftime("%j"))
    return (day_of_year * 4 + slot) % 12


def _build_hso_post(slot: int, platform: str) -> dict:
    """
    Build a full FRS-compliant Hook-Story-Offer post for this slot + platform.
    Uses STRATEGY.py content rotation — NOT random topic selection.
    FRS Pillar 2: Every output instance must validate Hook + Story + Offer.

    Returns:
        {
            "topic": str,
            "visual_prompt": str,     — short descriptive prompt for image/video generation
            "caption": str,           — HSO-structured caption for the post
            "full_hso_prompt": str,   — full Hook/Story/Offer breakdown
            "being": str,             — which AI being is featured
            "persona_segment": str,   — target audience segment
            "slot_label": str,        — slot name (Morning Inspiration, etc.)
            "platform_tone": str,
            "content_type": str,
            "offer": str,
        }
    """
    from vega.STRATEGY import get_content_rotation_item, build_hso_prompt, get_slot_config

    rotation_index = _get_rotation_index(slot)
    item = get_content_rotation_item(rotation_index)
    hso = build_hso_prompt(item["topic"], platform, slot)
    slot_cfg = get_slot_config(slot)

    return {
        "topic": item["topic"],
        "visual_prompt": hso["visual_prompt"],
        "caption": hso["caption_short"],
        "full_hso_prompt": hso["prompt"],
        "being": hso["being"],
        "persona_segment": item["persona"]["segment"],
        "slot_label": slot_cfg["label"],
        "platform_tone": hso["platform_tone"],
        "content_type": hso["content_type"],
        "offer": hso["offer"],
    }


def _use_brollbaby() -> bool:
    """50/50 chance of using brollbaby vs new AI generation."""
    return random.random() < 0.5


def _alert_everett(message: str) -> None:
    """
    Alert Everett that content is ready to post.
    Uses macOS 'say' command + prints to terminal.
    Rule 1: This must actually reach Everett — not silently logged.
    """
    print(f"\n{'='*60}")
    print(f"🔔 VEGA ALERT — {datetime.now().strftime('%I:%M %p')}")
    print(message)
    print(f"{'='*60}\n")

    # macOS voice alert
    if sys.platform == "darwin":
        safe_msg = message.replace('"', "'")[:200]
        os.system(f'say -v Daniel "vega alert. {safe_msg}"')


# ── Content Generation ─────────────────────────────────────────────────────────

def generate_post_all_platforms(slot: int) -> None:
    """
    Generate FRS-compliant content for ALL platforms at this time slot.
    Each platform gets its own HSO-structured post.
    Alerts Everett when all are ready.
    FRS Pillar 2: content_type and tone are platform-optimized per the matrix.
    """
    method = "brollbaby" if _use_brollbaby() else "new"
    results = []

    # Build the HSO post for the primary platform (instagram as reference)
    # Each platform-specific call will get its own platform-tuned version
    try:
        reference_post = _build_hso_post(slot, "instagram")
        topic = reference_post["topic"]
        being = reference_post["being"]
        slot_label = reference_post["slot_label"]
    except Exception as e:
        logger.error(f"[vega.Daily] Slot {slot+1} — FRS content build failed: {e}")
        topic = "The Christman AI Project — AI that serves humanity"
        being = "Luma Cognify AI"
        slot_label = f"Slot {slot+1}"

    logger.info(f"[vega.Daily] {slot_label} | ALL PLATFORMS | {method} | {topic[:50]}")

    for platform in ALL_PLATFORMS:
        result = generate_post(slot, platform, topic, method)
        results.append(result)

    ready = [r for r in results if r.get("status") == "ok"]
    failed = [r for r in results if r.get("status") != "ok"]

    summary = (
        f"{slot_label} complete — {len(ready)}/{len(ALL_PLATFORMS)} platforms ready\n"
        f"Being: {being}\n"
        f"Topic: {topic}\n"
        f"Method: {method}\n"
    )
    if ready:
        summary += "✅ Ready: " + ", ".join(r["platform"].upper() for r in ready) + "\n"
    if failed:
        summary += "❌ Failed: " + ", ".join(r["platform"].upper() for r in failed) + "\n"
    summary += "→ Review files and post when ready."

    _alert_everett(summary)


def generate_post(
    slot: int,
    platform: str = "instagram",
    topic: Optional[str] = None,
    method: Optional[str] = None,
) -> dict:
    """
    Generate one FRS-compliant social media post.

    - Builds Hook-Story-Offer structure via STRATEGY (Pillar 2)
    - Uses visual_prompt for image generation (not the raw topic string)
    - Stores HSO caption alongside the generated file in memory
    - Tries brollbaby or new AI generation per method flag

    Rule 13: Returns real file path or explicit failure — never fakes success.
    """
    method = method or ("brollbaby" if _use_brollbaby() else "new")

    # Build FRS-compliant HSO post — topic is used if provided (override), else rotation
    try:
        hso_post = _build_hso_post(slot, platform)
        if topic is None:
            topic = hso_post["topic"]
        visual_prompt = hso_post["visual_prompt"]
        caption = hso_post["caption"]
    except Exception as e:
        logger.warning(f"[vega.Daily] STRATEGY build failed ({e}), using topic as visual prompt")
        topic = topic or "Christman AI Project — AI serving humanity"
        visual_prompt = topic
        caption = topic

    logger.info(f"[vega.Daily] Slot {slot+1} | {platform.upper()} | {method} | {topic[:50]}")

    # ── LIFE2 Footage Scan ─────────────────────────────────────────────────────
    # Vega autonomously searches /Volumes/LIFE2 for real footage matching this post.
    # If LIFE2 isn't mounted, she logs it and continues — image gen is the fallback.
    footage_clips: list[dict] = []
    try:
        from vega.brollbaby.keyword_brain import extract_keywords
        from vega.video.broll import find_clips, scan_library
        from pathlib import Path

        if Path("/Volumes/LIFE2").exists():
            # Build/refresh the footage index on first run (cached after that)
            scan_library(base_path="/Volumes/LIFE2", rebuild_index=False)
            # Extract TCAP-aware keywords from the visual prompt
            keywords = extract_keywords(visual_prompt, max_keywords=8)
            footage_clips = find_clips(keywords, max_clips=5)
            if footage_clips:
                logger.info(
                    f"[vega.Daily] LIFE2 ✅ {len(footage_clips)} clips found for '{topic[:40]}': "
                    f"{[c.get('path', c.get('file', '?')) for c in footage_clips[:2]]}"
                )
            else:
                logger.info(
                    f"[vega.Daily] LIFE2 — no matching clips for '{topic[:40]}', "
                    "using image generation"
                )
        else:
            logger.warning(
                "[vega.Daily] LIFE2 not mounted — /Volumes/LIFE2 not found. "
                "Vega will use image generation. Mount LIFE2 for real footage."
            )
    except Exception as life2_err:
        logger.warning(f"[vega.Daily] LIFE2 scan failed (non-fatal): {life2_err}")
    # ── End LIFE2 Scan ─────────────────────────────────────────────────────────

    try:
        from vega.CORE import VegaCore
        core = VegaCore()

        # Use the visual_prompt (concise, descriptive) for image generation
        # NOT the full HSO caption — that's for the post copy, not the image prompt
        result = core.handle_image_prompt(
            prompt=visual_prompt,
            platform=platform,
            topic=topic,
            caption=caption,
        )

        if result.get("status") == "ok":
            output_path = result.get("output", {}).get("output_path", "unknown")
            post_id = result.get("post_id", "unknown")

            footage_line = ""
            if footage_clips:
                clip_paths = [c.get("path", c.get("file", "?")) for c in footage_clips[:3]]
                footage_line = f"LIFE2 Footage ({len(footage_clips)} clips): {', '.join(str(p) for p in clip_paths)}\n"

            msg = (
                f"Slot {slot+1}/4 ready for {platform.upper()}!\n"
                f"Being: {hso_post.get('being', topic)}\n"
                f"Topic: {topic}\n"
                f"File: {output_path}\n"
                f"Caption: {caption[:120]}...\n"
                f"{footage_line}"
                f"Method: {method}\n"
                f"→ Review and post when ready."
            )
            _alert_everett(msg)
            return {
                "status": "ok",
                "slot": slot + 1,
                "platform": platform,
                "topic": topic,
                "being": hso_post.get("being", ""),
                "method": method,
                "output_path": output_path,
                "post_id": post_id,
                "caption": caption,
                "persona_segment": hso_post.get("persona_segment", ""),
                "footage_clips": footage_clips,
            }
        else:
            reason = result.get("reason", "unknown error")
            logger.error(f"[vega.Daily] Slot {slot+1} {platform.upper()} failed: {reason}")
            _alert_everett(f"⚠️ Slot {slot+1}/4 FAILED on {platform.upper()}: {reason}")
            return {"status": "error", "slot": slot + 1, "platform": platform, "reason": reason}

    except Exception as e:
        logger.exception(f"[vega.Daily] Slot {slot+1} {platform.upper()} crashed: {e}")
        _alert_everett(f"⚠️ Slot {slot+1}/4 crashed on {platform.upper()}: {e}")
        return {"status": "error", "slot": slot + 1, "platform": platform, "reason": str(e)}


# ── Scheduler ──────────────────────────────────────────────────────────────────

def run_daily_engine() -> None:
    """
    Start the APScheduler-based daily engine.
    Fires 4 FRS-compliant content generation jobs per day.
    Runs until killed.

    Usage:
        python -m vega.daily_engine
    """
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError:
        print("[vega.Daily] ERROR: apscheduler not installed. Run: pip install apscheduler>=3.10.0")
        sys.exit(1)

    # Import FRS schedule so slots are always in sync with STRATEGY.py
    try:
        from vega.STRATEGY import get_posting_schedule, get_frs_summary
        schedule = get_posting_schedule()
        frs = get_frs_summary()
        print(f"[vega.Daily] FRS loaded — {frs['audience_personas']} personas, "
              f"{frs['content_rotation_depth']}-item rotation, "
              f"{frs['vanity_metrics_rejected']} vanity metrics rejected")
    except Exception as e:
        logger.warning(f"[vega.Daily] Could not load FRS summary: {e}. Using hardcoded schedule.")
        schedule = [
            {"slot": 1, "hour": 8,  "minute": 0, "label": "Morning Inspiration"},
            {"slot": 2, "hour": 11, "minute": 0, "label": "Product Showcase"},
            {"slot": 3, "hour": 15, "minute": 0, "label": "Community Story"},
            {"slot": 4, "hour": 19, "minute": 0, "label": "Evening Prime"},
        ]

    scheduler = BlockingScheduler()

    for slot_cfg in schedule:
        slot_num = slot_cfg["slot"]
        hour = slot_cfg["hour"]
        minute = slot_cfg["minute"]
        label = slot_cfg.get("label", f"Slot {slot_num}")

        scheduler.add_job(
            generate_post_all_platforms,
            trigger="cron",
            hour=hour,
            minute=minute,
            id=f"vega_post_{slot_num}",
            args=[slot_num],
            replace_existing=True,
        )
        print(f"  {hour:02d}:{minute:02d} → {label} — Instagram, TikTok, LinkedIn, Facebook, X, Clapper")

    print("\n[vega.Daily] Engine started — 4 FRS-compliant posts/day across ALL platforms")
    print("  HSO framework active — Hook + Story + Offer on every post")
    print("  Content rotation: 12-mission-topic cycle (no repetition)")
    print("  Everett alerted by voice when each slot is ready to post.")
    print("  Running — no terminal needed after launch.\n")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n[vega.Daily] Stopped.")
        scheduler.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_daily_engine()
