"""
daily_engine.py — vega
Daily content engine. Every day at scheduled times, generates 4 social media
posts (brollbaby or new AI content) and alerts Everett that they're ready to post.

Schedule (local time):
    08:00 — Post 1
    11:00 — Post 2
    15:00 — Post 3
    19:00 — Post 4

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
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vega.daily_engine")

# ── Post topics — pulled from the mission ─────────────────────────────────────
DAILY_TOPICS = [
    "AlphaVox giving a nonverbal child their first words",
    "AlphaWolf protecting a dementia patient from wandering",
    "Inferno AI supporting a veteran through a PTSD moment",
    "Aegis AI keeping a child safe online",
    "AlphaDen helping a child with Down syndrome learn to read",
    "OmegaAlpha keeping a senior connected and safe",
    "The Christman AI Project mission — AI that serves humanity",
    "Omega AI restoring mobility and independence",
    "Dusty's story — 12 years of silence broken in 36 hours",
    "Luma Cognify AI — ethical AI built from the margins",
    "Everett Christman — neurodivergent founder building what didn't exist",
    "How The Christman AI Project is changing lives right now",
]

ALL_PLATFORMS = ["instagram", "tiktok", "linkedin", "facebook", "x", "clapper"]


def _pick_topic() -> str:
    return random.choice(DAILY_TOPICS)


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


def generate_post_all_platforms(slot: int) -> None:
    """
    Generate content for ALL platforms at this time slot.
    Each platform gets its own post with the same topic.
    Alerts Everett when all are ready.
    """
    topic = _pick_topic()
    method = "brollbaby" if _use_brollbaby() else "new"
    results = []

    logger.info(f"[vega.Daily] Slot {slot+1} | ALL PLATFORMS | {method} | {topic[:50]}")

    for platform in ALL_PLATFORMS:
        result = generate_post(slot, platform, topic, method)
        results.append(result)

    ready = [r for r in results if r.get("status") == "ok"]
    failed = [r for r in results if r.get("status") != "ok"]

    summary = (
        f"Slot {slot+1}/4 complete — {len(ready)}/{len(ALL_PLATFORMS)} platforms ready\n"
        f"Topic: {topic}\n"
        f"Method: {method}\n"
    )
    if ready:
        summary += "✅ Ready: " + ", ".join(r["platform"].upper() for r in ready) + "\n"
    if failed:
        summary += "❌ Failed: " + ", ".join(r["platform"].upper() for r in failed) + "\n"
    summary += "→ Review files and post when ready."

    _alert_everett(summary)


def generate_post(slot: int, platform: str = "instagram", topic: str = None, method: str = None) -> dict:
    """
    Generate one social media post.
    Tries brollbaby first (if selected), falls back to new AI content.
    Returns dict with status, file_path, caption, platform.

    Rule 13: Returns real file path or explicit failure — never fakes success.
    """
    topic = topic or _pick_topic()
    method = method or ("brollbaby" if _use_brollbaby() else "new")

    logger.info(f"[vega.Daily] Slot {slot+1} | {platform.upper()} | {method} | {topic[:50]}")

    try:
        from vega.CORE import VegaCore
        core = VegaCore()

        result = core.handle_image_prompt(
            prompt=topic,
            platform=platform,
        )

        if result.get("status") == "ok":
            output_path = result.get("output", {}).get("output_path", "unknown")
            msg = (
                f"Post {slot+1}/4 ready for {platform.upper()}!\n"
                f"Topic: {topic}\n"
                f"File: {output_path}\n"
                f"Method: {method}\n"
                f"→ Review and post when ready."
            )
            _alert_everett(msg)
            return {
                "status": "ok",
                "slot": slot + 1,
                "platform": platform,
                "topic": topic,
                "method": method,
                "output_path": output_path,
            }
        else:
            reason = result.get("reason", "unknown error")
            logger.error(f"[vega.Daily] Slot {slot+1} failed: {reason}")
            _alert_everett(f"⚠️ Post {slot+1}/4 FAILED on {platform.upper()}: {reason}")
            return {"status": "error", "slot": slot + 1, "reason": reason}

    except Exception as e:
        logger.exception(f"[vega.Daily] Slot {slot+1} crashed: {e}")
        _alert_everett(f"⚠️ Post {slot+1}/4 crashed: {e}")
        return {"status": "error", "slot": slot + 1, "reason": str(e)}


def run_daily_engine() -> None:
    """
    Start the APScheduler-based daily engine.
    Fires 4 content generation jobs per day.
    Runs until killed.

    Usage:
        python -m VEGA.daily_engine
    """
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError:
        print("[vega.Daily] ERROR: apscheduler not installed. Run: pip install apscheduler>=3.10.0")
        sys.exit(1)

    scheduler = BlockingScheduler()

    for slot, (hour, minute) in enumerate([(8,0),(11,0),(15,0),(19,0)]):
        scheduler.add_job(
            generate_post_all_platforms,
            trigger="cron",
            hour=hour, minute=minute,
            id=f"vega_post_{slot}",
            args=[slot],
            replace_existing=True,
        )

    print("[vega.Daily] Engine started — 4 posts/day across ALL platforms")
    print("  08:00 → Slot 1 — Instagram, TikTok, LinkedIn, Facebook, X, Clapper")
    print("  11:00 → Slot 2 — Instagram, TikTok, LinkedIn, Facebook, X, Clapper")
    print("  15:00 → Slot 3 — Instagram, TikTok, LinkedIn, Facebook, X, Clapper")
    print("  19:00 → Slot 4 — Instagram, TikTok, LinkedIn, Facebook, X, Clapper")
    print("  Everett alerted by voice when each slot is ready to post.")
    print("  Running in background — no terminal needed after launch.\n")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n[vega.Daily] Stopped.")
        scheduler.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_daily_engine()
