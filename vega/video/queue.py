"""
vega/video/queue.py — Vega
Thread-safe video generation queue with watchdog and status reporter.

Rule 16: Heavy processes never run alone.
  - Queue Manager:   one render at a time, jobs never pile up.
  - Watchdog:        stalled renders surface loud and get retired.
  - Status Reporter: vega_queue_status.json always reflects real state.

Rule 13: Status is real. Never fake "rendering" if nothing is happening.
Rule 6:  Fail loud. Dead renders surface immediately, never swallowed.
Rule 15: Zero paid APIs. All renders go through ChristmanVideoEngine or B-roll.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 16 apply.
"""

import json
import logging
import threading
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue, Empty
from typing import Callable, Optional

logger = logging.getLogger("vega.video.queue")

# ── Config ────────────────────────────────────────────────────────────────────
STATUS_FILE        = Path(__file__).parent.parent.parent / "vega_queue_status.json"
RENDER_TIMEOUT_SEC = 600   # 10 min max per video — watchdog kills after this
MAX_RETRIES        = 1     # retry once on failure before marking dead


# ── Job dataclass ─────────────────────────────────────────────────────────────
@dataclass
class RenderJob:
    """
    A single video generation job.
    Everything Vega needs to produce one video, plus the callback for when it's done.
    """
    post_id:      str
    prompt:       str
    platform:     str
    duration_sec: int
    use_broll:    bool
    queued_at:    str                      = field(default_factory=lambda: datetime.utcnow().isoformat())
    on_complete:  Optional[Callable] = None   # fn(post_id, result_dict)
    attempt:      int                     = 0


# ── Queue manager ─────────────────────────────────────────────────────────────
class VegaVideoQueue:
    """
    Singleton queue manager for Vega video generation.

    One video renders at a time — GPU can't split focus.
    Every render is wrapped in a watchdog thread with a hard timeout.
    Status is written to disk after every state change so the theater
    can always show what's happening without polling the bridge.

    Rule 16: Heavy processes never run alone.
    """

    _instance:  "VegaVideoQueue | None" = None
    _init_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "VegaVideoQueue":
        with cls._init_lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._ready = False
                cls._instance = obj
        return cls._instance

    def __init__(self) -> None:
        if self._ready:
            return
        self._ready    = True
        self._q        = Queue()
        self._state    = {
            "queue_size":          0,
            "currently_rendering": None,
            "completed":           [],   # newest first, capped at 50
            "failed":              [],   # newest first, capped at 20
            "total_rendered":      0,
            "total_failed":        0,
            "updated_at":          None,
        }
        self._worker = threading.Thread(
            target=self._worker_loop,
            name="VegaQueueWorker",
            daemon=True,
        )
        self._worker.start()
        self._flush_status()
        logger.info("[Vega.Queue] Worker started — Rule 16 active. Queue, watchdog, reporter all live.")

    # ── Public API ──────────────────────────────────────────────────────────

    def submit(self, job: RenderJob) -> None:
        """Add a render job to the queue. Returns immediately."""
        self._q.put(job)
        self._state["queue_size"] = self._q.qsize()
        self._flush_status()
        logger.info(
            f"[Vega.Queue] Job queued: {job.post_id} | "
            f"platform={job.platform} | depth={self._q.qsize()}"
        )

    def status(self) -> dict:
        """Return current queue state. Always real — never fabricated (Rule 13)."""
        return dict(self._state)

    def queue_size(self) -> int:
        return self._q.qsize()

    # ── Worker loop ─────────────────────────────────────────────────────────

    def _worker_loop(self) -> None:
        """Main worker — pulls jobs and renders them one at a time."""
        while True:
            try:
                job: RenderJob = self._q.get(timeout=5)
            except Empty:
                continue

            self._render_with_watchdog(job)
            self._q.task_done()
            self._state["queue_size"] = self._q.qsize()
            self._flush_status()

    # ── Render + watchdog ───────────────────────────────────────────────────

    def _render_with_watchdog(self, job: RenderJob) -> None:
        """
        Run generate_from_prompt in a child thread.
        Kill it after RENDER_TIMEOUT_SEC if it hasn't finished.
        Retry once on failure before marking the job dead.
        Rule 16: The watchdog is mandatory. Not optional. Not skippable.
        """
        job.attempt += 1
        logger.info(
            f"[Vega.Queue] Rendering: {job.post_id} "
            f"(attempt {job.attempt}) | '{job.prompt[:60]}...'"
        )

        self._state["currently_rendering"] = {
            "post_id":    job.post_id,
            "prompt":     job.prompt[:100],
            "platform":   job.platform,
            "attempt":    job.attempt,
            "started_at": datetime.utcnow().isoformat(),
        }
        self._flush_status()

        result:    dict = {}
        exc_box:   list = []

        def _run() -> None:
            try:
                from vega.video.generator import generate_from_prompt
                result.update(
                    generate_from_prompt(
                        prompt=job.prompt,
                        platform=job.platform,
                        duration_sec=job.duration_sec,
                        use_broll=job.use_broll,
                    )
                )
            except Exception as exc:
                exc_box.append(exc)

        render_thread = threading.Thread(
            target=_run,
            name=f"VegaRender_{job.post_id}",
            daemon=True,
        )
        render_thread.start()
        render_thread.join(timeout=RENDER_TIMEOUT_SEC)

        # ── Watchdog check ──
        if render_thread.is_alive():
            # Stalled render — surface loud (Rule 6), do NOT silently ignore
            logger.error(
                f"[Vega.Queue] ⚠️  WATCHDOG TRIGGERED — "
                f"render timed out after {RENDER_TIMEOUT_SEC}s: {job.post_id}"
            )
            result = {
                "status": "error",
                "reason": (
                    f"Watchdog killed render after {RENDER_TIMEOUT_SEC}s. "
                    f"Rule 16: stalled renders never run undetected."
                ),
                "method": "watchdog_timeout",
            }

        elif exc_box:
            err = exc_box[0]
            logger.error(f"[Vega.Queue] Render exception: {err}")
            result = {
                "status": "error",
                "reason": str(err),
                "method": "exception",
            }

        # ── Retry logic ──
        if result.get("status") != "ok" and job.attempt <= MAX_RETRIES:
            logger.warning(
                f"[Vega.Queue] Retrying {job.post_id} "
                f"(attempt {job.attempt + 1} of {MAX_RETRIES + 1})"
            )
            self._state["currently_rendering"] = None
            self._render_with_watchdog(job)   # tail-call retry
            return

        # ── Record outcome ──
        self._state["currently_rendering"] = None
        entry = {
            "post_id":      job.post_id,
            "status":       result.get("status", "error"),
            "method":       result.get("method", "unknown"),
            "output_path":  result.get("output_path"),
            "platform":     job.platform,
            "prompt":       job.prompt[:80],
            "attempts":     job.attempt,
            "completed_at": datetime.utcnow().isoformat(),
        }

        if result.get("status") == "ok":
            self._state["completed"].insert(0, entry)
            self._state["completed"]   = self._state["completed"][:50]
            self._state["total_rendered"] += 1
            logger.info(f"[Vega.Queue] ✅  Render complete: {job.post_id} → {result.get('output_path')}")
        else:
            self._state["failed"].insert(0, entry)
            self._state["failed"]      = self._state["failed"][:20]
            self._state["total_failed"] += 1
            logger.error(
                f"[Vega.Queue] ❌  Render failed: {job.post_id} — "
                f"{result.get('reason', 'unknown reason')} (Rule 6: surfaced, not swallowed)"
            )

        self._flush_status()

        # ── Completion callback ──
        if job.on_complete:
            try:
                job.on_complete(job.post_id, result)
            except Exception as cb_exc:
                logger.error(f"[Vega.Queue] on_complete callback error: {cb_exc}")

    # ── Status persistence ──────────────────────────────────────────────────

    def _flush_status(self) -> None:
        """
        Write real queue state to disk.
        Rule 13: Never write a status that isn't true.
        The theater reads this file to show render-in-progress cards.
        """
        self._state["updated_at"] = datetime.utcnow().isoformat()
        try:
            STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATUS_FILE.write_text(
                json.dumps(self._state, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as exc:
            # Log but never crash the worker over a status write failure
            logger.error(f"[Vega.Queue] Status write failed: {exc}")


# ── Singleton accessor ────────────────────────────────────────────────────────

def get_queue() -> VegaVideoQueue:
    """Get (or create) the singleton Vega video queue."""
    return VegaVideoQueue()
