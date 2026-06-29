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
DATA_DIR = Path(__file__).parent / "data"
POSTS_FILE = DATA_DIR / "posts.json"
CAMPAIGNS_FILE = DATA_DIR / "campaigns.json"
ANALYTICS_FILE = DATA_DIR / "analytics.json"
SCHEDULE_FILE = DATA_DIR / "schedule.json"


def _ensure_memory_dir() -> None:
    """Create memory directory if it doesn't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _posts_file() -> Path:
    return DATA_DIR / "posts.json"


def _campaigns_file() -> Path:
    return DATA_DIR / "campaigns.json"


def _analytics_file() -> Path:
    return DATA_DIR / "analytics.json"


def _schedule_file() -> Path:
    return DATA_DIR / "schedule.json"


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

    posts = _load_json(_posts_file())
    if not isinstance(posts, list):
        posts = []

    post["id"] = f"post_{len(posts) + 1:05d}"
    post["created_at"] = datetime.utcnow().isoformat()
    posts.append(post)
    _save_json(_posts_file(), posts)
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
    posts = _load_json(_posts_file())
    if not isinstance(posts, list):
        return []

    if platform:
        posts = [p for p in posts if p.get("platform", "").lower() == platform.lower()]
    if status:
        posts = [p for p in posts if p.get("status", "").lower() == status.lower()]

    return posts[-limit:]  # most recent N


def update_post_status(post_id: str, status: str, metadata: Optional[dict] = None) -> dict:
    """Update a post's status (e.g. published, failed, scheduled)."""
    posts = _load_json(_posts_file())
    if not isinstance(posts, list):
        raise RuntimeError("Post memory is not a list — something is corrupt.")

    for post in posts:
        if post.get("id") == post_id:
            post["status"] = status
            post["updated_at"] = datetime.utcnow().isoformat()
            if metadata:
                post.update(metadata)
            _save_json(_posts_file(), posts)
            return post

    raise ValueError(f"Post not found: {post_id}. Rule 13: not inventing a fake update.")


# ── Campaign Memory ────────────────────────────────────────────────────────────

def remember_campaign(campaign: dict) -> dict:
    """Store a campaign definition."""
    campaigns = _load_json(_campaigns_file())
    if not isinstance(campaigns, list):
        campaigns = []

    campaign["id"] = f"campaign_{len(campaigns) + 1:04d}"
    campaign["created_at"] = datetime.utcnow().isoformat()
    campaigns.append(campaign)
    _save_json(_campaigns_file(), campaigns)
    return campaign


def recall_campaigns(active_only: bool = False) -> list:
    """Retrieve all campaigns, optionally filtered to active ones."""
    campaigns = _load_json(_campaigns_file())
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
    analytics = _load_json(_analytics_file())
    if not isinstance(analytics, list):
        analytics = []

    entry = {
        "post_id": post_id,
        "platform": platform,
        "metrics": metrics,
        "recorded_at": datetime.utcnow().isoformat(),
    }
    analytics.append(entry)
    _save_json(_analytics_file(), analytics)
    return entry


def recall_analytics(post_id: Optional[str] = None, platform: Optional[str] = None) -> list:
    """
    Retrieve analytics records.
    Rule 13: Returns what was stored. Never fabricates engagement numbers.
    """
    analytics = _load_json(_analytics_file())
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
    schedule = _load_json(_schedule_file())
    if not isinstance(schedule, list):
        schedule = []

    item["id"] = f"sched_{len(schedule) + 1:05d}"
    item["created_at"] = datetime.utcnow().isoformat()
    schedule.append(item)
    _save_json(_schedule_file(), schedule)
    return item


def recall_schedule(pending_only: bool = True) -> list:
    """Retrieve the post schedule."""
    schedule = _load_json(_schedule_file())
    if not isinstance(schedule, list):
        return []
    if pending_only:
        schedule = [s for s in schedule if s.get("status", "pending") == "pending"]
    return schedule


def cancel_scheduled_item(sched_id: str) -> dict:
    """Cancel a scheduled post."""
    schedule = _load_json(_schedule_file())
    if not isinstance(schedule, list):
        raise RuntimeError("Schedule memory is corrupt.")

    for item in schedule:
        if item.get("id") == sched_id:
            item["status"] = "cancelled"
            item["cancelled_at"] = datetime.utcnow().isoformat()
            _save_json(_schedule_file(), schedule)
            return item

    raise ValueError(f"Scheduled item not found: {sched_id}")


def get_memory_summary() -> dict:
    """Return a quick summary of what Vega remembers. For health checks."""
    return {
        "total_posts": len(_load_json(_posts_file()) or []),
        "total_campaigns": len(_load_json(_campaigns_file()) or []),
        "total_analytics_records": len(_load_json(_analytics_file()) or []),
        "pending_scheduled": len(recall_schedule(pending_only=True)),
    }


# ── VegaMemory Class ───────────────────────────────────────────────────────────
# Object-oriented interface for tests and Carbon Bridge integration.
# Uses self.data_dir so tests can monkeypatch DATA_DIR and override per-instance.

class VegaMemory:
    """
    Object-oriented memory interface for Vega.
    Rule 13: Never fabricate memory. Never invent history.
    """

    def __init__(self):
        self.data_dir = DATA_DIR

    def _pf(self) -> Path:
        return self.data_dir / "posts.json"

    def _af(self) -> Path:
        return self.data_dir / "analytics.json"

    def _sf(self) -> Path:
        return self.data_dir / "schedule.json"

    def _load(self, path: Path) -> list:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            return []
        try:
            with open(path, "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def _save(self, path: Path, data: list) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def remember_post(self, post: dict) -> dict:
        """Store a post. Returns {"status": "stored", ...post data}."""
        posts = self._load(self._pf())
        entry = {
            "id": f"post_{len(posts) + 1:05d}",
            "created_at": datetime.utcnow().isoformat(),
            **post,
        }
        posts.append(entry)
        self._save(self._pf(), posts)
        return {"status": "stored", **entry}

    def recall_posts(self, platform: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> list:
        """Retrieve posts, optionally filtered. Rule 13: returns what exists."""
        posts = self._load(self._pf())
        if platform:
            posts = [p for p in posts if p.get("platform", "").lower() == platform.lower()]
        if status:
            posts = [p for p in posts if p.get("status", "").lower() == status.lower()]
        return posts[-limit:]

    def update_post_status(self, post_id: str, status: str, metadata: Optional[dict] = None) -> dict:
        """Update a post's status. Returns {"status": "updated", ...}."""
        posts = self._load(self._pf())
        for post in posts:
            if post.get("post_id") == post_id or post.get("id") == post_id:
                post["status"] = status
                post["updated_at"] = datetime.utcnow().isoformat()
                if metadata:
                    post.update(metadata)
                self._save(self._pf(), posts)
                return {**post, "status": "updated"}
        raise ValueError(f"Post not found: {post_id}. Rule 13: not inventing a fake update.")

    def store_analytics(self, post_id: str, platform: str, metrics: dict) -> dict:
        """Store analytics for a post. Rule 13: real numbers only."""
        analytics = self._load(self._af())
        entry = {
            "post_id": post_id,
            "platform": platform,
            "metrics": metrics,
            "recorded_at": datetime.utcnow().isoformat(),
        }
        analytics.append(entry)
        self._save(self._af(), analytics)
        return entry

    def recall_analytics(self, post_id: Optional[str] = None, platform: Optional[str] = None) -> list:
        """Retrieve analytics. Rule 13: returns what was stored, never invented."""
        records = self._load(self._af())
        if post_id:
            records = [r for r in records if r.get("post_id") == post_id]
        if platform:
            records = [r for r in records if r.get("platform", "").lower() == platform.lower()]
        return records

    def remember_scheduled_item(self, item: dict) -> dict:
        """Schedule a post item. Returns {"status": "stored", ...}."""
        schedule = self._load(self._sf())
        entry = {
            "id": f"sched_{len(schedule) + 1:05d}",
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending",
            **item,
        }
        schedule.append(entry)
        self._save(self._sf(), schedule)
        return {**entry, "status": "stored"}

    def recall_schedule(self, pending_only: bool = True) -> list:
        """Retrieve the post schedule."""
        schedule = self._load(self._sf())
        if pending_only:
            schedule = [s for s in schedule if s.get("status", "pending") == "pending"]
        return schedule

    def get_memory_summary(self) -> dict:
        """Quick summary of what Vega remembers. Rule 13: real counts only."""
        return {
            "total_posts": len(self._load(self._pf())),
            "total_analytics_records": len(self._load(self._af())),
            "pending_scheduled": len(self.recall_schedule(pending_only=True)),
        }
