"""
analytics/tracker.py — Vega
Pulls real post metrics from platform APIs and stores them in MEMORY.

Rule 13: Every number comes from a real API call. We never invent engagement data.
         If the API returns nothing, we return nothing — not zeros we made up.
Rule 6:  Platform errors bubble up with context, never silently swallowed.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply. Rule 13 is gospel.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("vega.analytics.tracker")

# Platforms Vega tracks
TRACKED_PLATFORMS = ["instagram", "tiktok", "youtube", "facebook", "linkedin", "x"]


class VegaAnalyticsTracker:
    """
    Fetches and stores post analytics from all 6 platforms.

    Usage:
        tracker = VegaAnalyticsTracker(memory=memory_instance, broadcast_fn=core.broadcast)
        result = tracker.refresh_post(post_id="abc123", platform="instagram",
                                       platform_post_id="17841234567")
        summary = tracker.refresh_all(posts=[...])
    """

    def __init__(self, memory=None, broadcast_fn=None):
        self._memory = memory
        self._broadcast = broadcast_fn

    def refresh_post(
        self,
        post_id: str,
        platform: str,
        platform_post_id: str,
    ) -> dict:
        """
        Fetch current metrics for a single post from the platform API.
        Stores in memory and returns the metric dict.

        Rule 13: Returns {"status": "no_data"} if the API gives nothing — never fabricates.
        """
        if platform not in TRACKED_PLATFORMS:
            return {"status": "error", "reason": f"Platform '{platform}' not tracked by Vega"}

        try:
            from vega.scheduler.platforms import get_platform
            client = get_platform(platform)
            result = client.get_metrics(platform_post_id)
        except EnvironmentError as e:
            logger.error(f"[Vega.Tracker] Missing API keys for {platform}: {e}")
            return {"status": "error", "reason": str(e)}
        except Exception as e:
            logger.error(f"[Vega.Tracker] Failed to fetch metrics for {post_id} on {platform}: {e}")
            return {"status": "error", "reason": str(e)}

        if result.get("status") != "ok":
            return result

        metrics = result.get("metrics", {})
        if not metrics:
            # Rule 13: Don't store empty or fabricated data
            return {"status": "no_data", "post_id": post_id, "platform": platform}

        # Attach timestamp so we know when these numbers were pulled
        metrics["fetched_at"] = datetime.utcnow().isoformat()

        if self._memory:
            try:
                self._memory.store_analytics(post_id, platform, metrics)
            except Exception as e:
                logger.warning(f"[Vega.Tracker] Memory store failed for {post_id}: {e}")

        logger.info(f"[Vega.Tracker] ✅ Updated metrics for {post_id} on {platform}: {metrics}")

        return {
            "status": "ok",
            "post_id": post_id,
            "platform": platform,
            "platform_post_id": platform_post_id,
            "metrics": metrics,
        }

    def refresh_all(self, posts: list[dict]) -> dict:
        """
        Refresh metrics for a list of posts.

        Each post dict must contain: post_id, platform, platform_post_id
        Returns a summary of what succeeded, what failed, what had no data.

        Rule 13: Results reflect actual API responses. No fill-in.
        """
        results = {"refreshed": [], "failed": [], "no_data": [], "skipped": []}

        for post in posts:
            post_id = post.get("post_id")
            platform = post.get("platform")
            platform_post_id = post.get("platform_post_id")

            if not all([post_id, platform, platform_post_id]):
                results["skipped"].append({
                    "post": post,
                    "reason": "Missing post_id, platform, or platform_post_id",
                })
                continue

            r = self.refresh_post(post_id, platform, platform_post_id)
            if r.get("status") == "ok":
                results["refreshed"].append(r)
            elif r.get("status") == "no_data":
                results["no_data"].append(r)
            else:
                results["failed"].append(r)

        summary = (
            f"[Vega.Tracker] Analytics refresh: "
            f"{len(results['refreshed'])} updated, "
            f"{len(results['failed'])} failed, "
            f"{len(results['no_data'])} no data, "
            f"{len(results['skipped'])} skipped"
        )
        logger.info(summary)

        if self._broadcast:
            self._broadcast(summary, context="vega_analytics")

        return {"status": "complete", **results}

    def get_summary_for_post(self, post_id: str) -> dict:
        """
        Pull the full analytics history for a post from memory and compute summary stats.
        Rule 13: Only uses stored (real) data. Never invents averages.
        """
        if not self._memory:
            return {"status": "error", "reason": "No memory backend attached to tracker"}

        try:
            all_records = self._memory.recall_analytics(post_id, platform=None)
        except Exception as e:
            return {"status": "error", "reason": str(e)}

        if not all_records:
            return {"status": "no_data", "post_id": post_id}

        # Group by platform
        by_platform: dict[str, list] = {}
        for record in all_records:
            p = record.get("platform", "unknown")
            by_platform.setdefault(p, []).append(record)

        summary = {"post_id": post_id, "by_platform": {}}
        for platform, records in by_platform.items():
            # Latest snapshot
            latest = max(records, key=lambda r: r.get("fetched_at", ""), default=None)
            if latest:
                summary["by_platform"][platform] = {
                    "latest": latest.get("metrics", {}),
                    "snapshots": len(records),
                }

        return {"status": "ok", **summary}

    def get_performance_table(self, posts: list[dict]) -> list[dict]:
        """
        Build a flat performance table across all posts for visualizer consumption.
        Returns a list of rows: {post_id, platform, metric_name, value, fetched_at}

        Rule 13: Only includes rows with real stored data.
        """
        if not self._memory:
            return []

        rows = []
        for post in posts:
            post_id = post.get("post_id")
            platform = post.get("platform")
            if not post_id or not platform:
                continue

            try:
                records = self._memory.recall_analytics(post_id, platform=platform)
            except Exception:
                continue

            for record in records:
                metrics = record.get("metrics", {})
                fetched_at = metrics.pop("fetched_at", None)
                for metric_name, value in metrics.items():
                    if isinstance(value, (int, float)):
                        rows.append({
                            "post_id": post_id,
                            "platform": platform,
                            "metric": metric_name,
                            "value": value,
                            "fetched_at": fetched_at,
                        })

        return rows
