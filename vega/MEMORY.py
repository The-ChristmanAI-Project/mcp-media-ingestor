"""
MEMORY.py — Vega
Campaign history, post memory, analytics storage.
Rule 13: Never fabricate memory. Never invent history.
If memory is empty, say so. Do not fill it with fiction.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply. Rule 13 is gospel.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vega.memory")

# Default memory directory — lives inside the bridge project
MEMORY_DIR = Path(__file__).parent / "data"
POSTS_FILE = MEMORY_DIR / "posts.json"
CAMPAIGNS_FILE = MEMORY_DIR / "campaigns.json"
ANALYTICS_FILE = MEMORY_DIR / "analytics.json"
SCHEDULE_FILE = MEMORY_DIR / "schedule.json"


def _ensure_memory_dir() -> None:
    """Create memory directory if it doesn't exist."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> list | dict:
    """Load JSON from path. Returns empty list if file doesn't exist."""
    if not path.exists():
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"[Vega.Memory] Corrupt JSON at {path}: {e}")
        raise RuntimeError(f"Memory file corrupted: {path}. Do not fake recovery. (Rule 13)")


def _save_json(path: Path, data: list | dict) -> None:
    """Persist JSON to path. Fails loud if it breaks. (Rule 6)"""
    _ensure_memory_dir()
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"[Vega.Memory] Write failed at {path}: {e}")
        raise RuntimeError(f"Memory write failed: {path} — {e}")


# ── Post Memory ────────────────────────────────────────────────────────────────

def remember_post(post: dict) -> dict:
    """
    Store a published or scheduled post.
    Required keys: platform, content_type, prompt, file_path, status
    """
    required = {"platform", "content_type", "prompt", "status"}
    missing = required - set(post.keys())
    if missing:
        raise ValueError(f"Post missing required fields: {missing}")

    posts = _load_json(POSTS_FILE)
    if not isinstance(posts, list):
        posts = []

    post["id"] = f"post_{len(posts) + 1:05d}"
    post["created_at"] = datetime.utcnow().isoformat()
    posts.append(post)
    _save_json(POSTS_FILE, posts)
    logger.info(f"[Vega.Memory] Post remembered: {post['id']} on {post['platform']}")
    return post


def recall_posts(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> list:
    """
    Retrieve posts, optionally filtered by platform and/or status.
    Rule 13: Returns what exists. Never invents what doesn't.
    """
    posts = _load_json(POSTS_FILE)
    if not isinstance(posts, list):
        return []

    if platform:
        posts = [p for p in posts if p.get("platform", "").lower() == platform.lower()]
    if status:
        posts = [p for p in posts if p.get("status", "").lower() == status.lower()]

    return posts[-limit:]  # most recent N


def update_post_status(post_id: str, status: str, metadata: Optional[dict] = None) -> dict:
    """Update a post's status (e.g. published, failed, scheduled)."""
    posts = _load_json(POSTS_FILE)
    if not isinstance(posts, list):
        raise RuntimeError("Post memory is not a list — something is corrupt.")

    for post in posts:
        if post.get("id") == post_id:
            post["status"] = status
            post["updated_at"] = datetime.utcnow().isoformat()
            if metadata:
                post.update(metadata)
            _save_json(POSTS_FILE, posts)
            return post

    raise ValueError(f"Post not found: {post_id}. Rule 13: not inventing a fake update.")


# ── Campaign Memory ────────────────────────────────────────────────────────────

def remember_campaign(campaign: dict) -> dict:
    """Store a campaign definition."""
    campaigns = _load_json(CAMPAIGNS_FILE)
    if not isinstance(campaigns, list):
        campaigns = []

    campaign["id"] = f"campaign_{len(campaigns) + 1:04d}"
    campaign["created_at"] = datetime.utcnow().isoformat()
    campaigns.append(campaign)
    _save_json(CAMPAIGNS_FILE, campaigns)
    return campaign


def recall_campaigns(active_only: bool = False) -> list:
    """Retrieve all campaigns, optionally filtered to active ones."""
    campaigns = _load_json(CAMPAIGNS_FILE)
    if not isinstance(campaigns, list):
        return []
    if active_only:
        campaigns = [c for c in campaigns if c.get("status") == "active"]
    return campaigns


# ── Analytics Memory ───────────────────────────────────────────────────────────

def store_analytics(post_id: str, platform: str, metrics: dict) -> dict:
    """
    Store analytics snapshot for a post.
    Metrics are real numbers pulled from platform APIs — not invented.
    """
    analytics = _load_json(ANALYTICS_FILE)
    if not isinstance(analytics, list):
        analytics = []

    entry = {
        "post_id": post_id,
        "platform": platform,
        "metrics": metrics,
        "recorded_at": datetime.utcnow().isoformat(),
    }
    analytics.append(entry)
    _save_json(ANALYTICS_FILE, analytics)
    return entry


def recall_analytics(post_id: Optional[str] = None, platform: Optional[str] = None) -> list:
    """
    Retrieve analytics records.
    Rule 13: Returns what was stored. Never fabricates engagement numbers.
    """
    analytics = _load_json(ANALYTICS_FILE)
    if not isinstance(analytics, list):
        return []

    if post_id:
        analytics = [a for a in analytics if a.get("post_id") == post_id]
    if platform:
        analytics = [a for a in analytics if a.get("platform", "").lower() == platform.lower()]

    return analytics


# ── Schedule Memory ────────────────────────────────────────────────────────────

def remember_scheduled_item(item: dict) -> dict:
    """Store a scheduled post item."""
    schedule = _load_json(SCHEDULE_FILE)
    if not isinstance(schedule, list):
        schedule = []

    item["id"] = f"sched_{len(schedule) + 1:05d}"
    item["created_at"] = datetime.utcnow().isoformat()
    schedule.append(item)
    _save_json(SCHEDULE_FILE, schedule)
    return item


def recall_schedule(pending_only: bool = True) -> list:
    """Retrieve the post schedule."""
    schedule = _load_json(SCHEDULE_FILE)
    if not isinstance(schedule, list):
        return []
    if pending_only:
        schedule = [s for s in schedule if s.get("status", "pending") == "pending"]
    return schedule


def cancel_scheduled_item(sched_id: str) -> dict:
    """Cancel a scheduled post."""
    schedule = _load_json(SCHEDULE_FILE)
    if not isinstance(schedule, list):
        raise RuntimeError("Schedule memory is corrupt.")

    for item in schedule:
        if item.get("id") == sched_id:
            item["status"] = "cancelled"
            item["cancelled_at"] = datetime.utcnow().isoformat()
            _save_json(SCHEDULE_FILE, schedule)
            return item

    raise ValueError(f"Scheduled item not found: {sched_id}")


def get_memory_summary() -> dict:
    """Return a quick summary of what Vega remembers. For health checks."""
    return {
        "total_posts": len(_load_json(POSTS_FILE) or []),
        "total_campaigns": len(_load_json(CAMPAIGNS_FILE) or []),
        "total_analytics_records": len(_load_json(ANALYTICS_FILE) or []),
        "pending_scheduled": len(recall_schedule(pending_only=True)),
    }
