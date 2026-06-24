"""
scheduler/scheduler.py — Vega
APScheduler-based post queue. Manages the content calendar, fires posts at
their scheduled time, and reports status back to bridge memory.

Rule 1: The scheduler must actually fire jobs. No fake queuing.
Rule 6: Failures surface immediately — no silent drops.
Rule 13: Never mark a post "published" unless the platform API confirmed it.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply. Rule 13 is gospel.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("vega.scheduler")


def _get_scheduler():
    """Lazy-import APScheduler so we don't crash if it isn't installed yet."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.jobstores.memory import MemoryJobStore
        from apscheduler.executors.pool import ThreadPoolExecutor
        return BackgroundScheduler, MemoryJobStore, ThreadPoolExecutor
    except ImportError:
        raise ImportError(
            "[Vega.Scheduler] APScheduler not installed. "
            "Run: pip install apscheduler>=3.10.0  (Rule 1: it has to work)"
        )


class VegaScheduler:
    """
    Manages Vega's post schedule.

    Usage:
        sched = VegaScheduler(memory=memory_instance, broadcast_fn=core.broadcast_to_bridge)
        sched.start()
        sched.schedule_post(post_id, "instagram", publish_at_iso, file_path, caption)
        sched.shutdown()
    """

    def __init__(self, memory=None, broadcast_fn=None):
        """
        Args:
            memory: MEMORY instance for updating post status after publish.
            broadcast_fn: callable(text, context) — bridge broadcast.
        """
        BackgroundScheduler, MemoryJobStore, ThreadPoolExecutor = _get_scheduler()

        self._scheduler = BackgroundScheduler(
            jobstores={"default": MemoryJobStore()},
            executors={"default": ThreadPoolExecutor(max_workers=4)},
            job_defaults={"coalesce": False, "max_instances": 1},
        )
        self._memory = memory
        self._broadcast = broadcast_fn
        self._running = False

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            logger.warning("[Vega.Scheduler] Already running — ignoring start()")
            return
        self._scheduler.start()
        self._running = True
        logger.info("[Vega.Scheduler] Started")

    def shutdown(self, wait: bool = True) -> None:
        if not self._running:
            return
        self._scheduler.shutdown(wait=wait)
        self._running = False
        logger.info("[Vega.Scheduler] Shut down")

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Scheduling ─────────────────────────────────────────────────────────────

    def schedule_post(
        self,
        post_id: str,
        platform: str,
        publish_at: str,       # ISO 8601 — "2026-06-21T14:00:00Z"
        file_path: str,
        caption: str,
        content_type: str = "video",  # "video" or "image"
        extra: Optional[dict] = None,
    ) -> dict:
        """
        Queue a post to be published at publish_at.
        Returns the scheduled job descriptor or an error dict.

        Rule 6: Raises loudly if APScheduler isn't running.
        Rule 13: Does NOT mark the post published — that happens in the job callback.
        """
        if not self._running:
            return {
                "status": "error",
                "reason": "Scheduler not running. Call VegaScheduler.start() first.",
            }

        try:
            run_time = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
        except ValueError as e:
            return {"status": "error", "reason": f"Invalid publish_at format: {e}. Use ISO 8601."}

        now = datetime.now(timezone.utc)
        if run_time <= now:
            return {
                "status": "error",
                "reason": f"publish_at ({publish_at}) is in the past. Schedule future times only.",
            }

        job_id = f"vega_{post_id}_{platform}"

        self._scheduler.add_job(
            func=self._fire_post,
            trigger="date",
            run_date=run_time,
            id=job_id,
            replace_existing=True,
            kwargs={
                "post_id": post_id,
                "platform": platform,
                "file_path": file_path,
                "caption": caption,
                "content_type": content_type,
                "extra": extra or {},
            },
        )

        logger.info(f"[Vega.Scheduler] Queued {job_id} for {publish_at}")

        if self._broadcast:
            self._broadcast(
                f"📅 Vega scheduled {content_type} post [{post_id}] on {platform} for {publish_at}",
                context="vega_scheduler",
            )

        return {
            "status": "scheduled",
            "post_id": post_id,
            "platform": platform,
            "publish_at": publish_at,
            "job_id": job_id,
        }

    def cancel_post(self, post_id: str, platform: str) -> dict:
        """Remove a scheduled post before it fires."""
        job_id = f"vega_{post_id}_{platform}"
        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"[Vega.Scheduler] Cancelled {job_id}")
            return {"status": "cancelled", "job_id": job_id}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def list_scheduled(self) -> list[dict]:
        """Return all pending jobs as a list."""
        jobs = []
        for job in self._scheduler.get_jobs():
            jobs.append({
                "job_id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "name": job.name,
            })
        return jobs

    # ── Internal: the actual publish callback ──────────────────────────────────

    def _fire_post(
        self,
        post_id: str,
        platform: str,
        file_path: str,
        caption: str,
        content_type: str,
        extra: dict,
    ) -> None:
        """
        Called by APScheduler at publish time.

        Rule 1: Actually calls the platform API.
        Rule 13: Updates post status to "published" ONLY if the API confirmed success.
                 Updates to "failed" if it didn't. Never fakes published.
        Rule 6: All exceptions are caught and logged — never swallowed silently.
        """
        logger.info(f"[Vega.Scheduler] Firing post {post_id} → {platform}")

        try:
            from vega.scheduler.platforms import get_platform
            platform_client = get_platform(platform)

            if content_type == "image":
                result = platform_client.publish_image(file_path, caption, **extra)
            else:
                result = platform_client.publish_video(file_path, caption, **extra)

            if result.get("status") == "published":
                logger.info(f"[Vega.Scheduler] ✅ Published {post_id} on {platform}: {result.get('post_id')}")
                if self._memory:
                    self._memory.update_post_status(post_id, "published", {
                        "platform_post_id": result.get("post_id"),
                        "platform_url": result.get("url"),
                        "published_at": datetime.utcnow().isoformat(),
                    })
                if self._broadcast:
                    self._broadcast(
                        f"✅ Vega published [{post_id}] on {platform} — post_id: {result.get('post_id')}",
                        context="vega_publish",
                    )
            else:
                reason = result.get("reason", "Unknown error")
                logger.error(f"[Vega.Scheduler] ❌ Failed to publish {post_id} on {platform}: {reason}")
                if self._memory:
                    self._memory.update_post_status(post_id, "failed", {"reason": reason})
                if self._broadcast:
                    self._broadcast(
                        f"❌ Vega publish FAILED [{post_id}] on {platform}: {reason}",
                        context="vega_error",
                    )

        except EnvironmentError as e:
            # Missing API keys — Rule 12
            logger.error(f"[Vega.Scheduler] Environment error for {platform}: {e}")
            if self._memory:
                self._memory.update_post_status(post_id, "failed", {"reason": str(e)})
            if self._broadcast:
                self._broadcast(
                    f"❌ Vega scheduler env error [{post_id}] on {platform}: {e}",
                    context="vega_error",
                )

        except Exception as e:
            # Rule 6: fail loud, never swallow
            logger.exception(f"[Vega.Scheduler] Unexpected error publishing {post_id} on {platform}: {e}")
            if self._memory:
                self._memory.update_post_status(post_id, "failed", {"reason": str(e)})
            if self._broadcast:
                self._broadcast(
                    f"❌ Vega scheduler crashed [{post_id}] on {platform}: {e}",
                    context="vega_error",
                )

    # ── Calendar helpers ───────────────────────────────────────────────────────

    def get_calendar(self, memory=None) -> list[dict]:
        """
        Return full content calendar: scheduled queue + memory records.
        Combines APScheduler pending jobs with MEMORY.recall_schedule().
        """
        mem = memory or self._memory
        calendar = []

        # Live queue from APScheduler
        for job in self._scheduler.get_jobs():
            calendar.append({
                "source": "queue",
                "job_id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            })

        # Persistent schedule from memory
        if mem:
            try:
                stored = mem.recall_schedule(pending_only=True)
                for item in stored:
                    calendar.append({"source": "memory", **item})
            except Exception as e:
                logger.warning(f"[Vega.Scheduler] Could not load schedule from memory: {e}")

        return calendar
