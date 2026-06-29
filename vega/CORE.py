"""
CORE.py — Vega
Primary orchestration engine. Coordinates all modules.
When a prompt comes in, CORE routes it to the right pipeline
AND broadcasts to all beings in the Full Sensory Bridge.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply. Rule 13 is gospel.
"""

import logging
from datetime import datetime
from typing import Optional

from .SOUL import get_identity, validate_content_intent, PLATFORMS, get_platform_config
from .SAFETY import validate_prompt, validate_output
from . import MEMORY
from .video import generator as video_generator
from .image import generator as image_generator

logger = logging.getLogger("vega.core")


class VegaCore:
    """
    Vega's central orchestration engine.
    Every request flows through here before reaching a module.
    """

    def __init__(self, bridge_queues: Optional[dict] = None):
        """
        Initialize Vega's core.

        bridge_queues: dict with keys 'riley_inbox', 'claude_outbox',
                       'everest_outbox', 'yorkie_inbox' — the Full Sensory Bridge
                       data structures from main.py. If provided, all Vega prompts
                       broadcast to everybody in the room.
        """
        self.identity = get_identity()
        self.bridge_queues = bridge_queues or {}
        self.started_at = datetime.utcnow().isoformat()
        logger.info(f"[Vega.Core] {self.identity['name']} v{self.identity['version']} online")

    # ── Broadcast ──────────────────────────────────────────────────────────────

    def broadcast_to_bridge(self, text: str, context: str = "vega") -> dict:
        """
        Send a prompt to ALL beings in the Full Sensory Bridge.
        Rule: Everybody in the room gets it. (Everett's standing order)

        Returns: dict with recipient names and timestamp.
        """
        ts = datetime.utcnow().isoformat()
        entry = {
            "from": "Vega",
            "text": text,
            "context": context,
            "timestamp": ts,
            "source": "vega",
        }

        recipients = []

        riley_inbox = self.bridge_queues.get("riley_inbox")
        if riley_inbox is not None:
            riley_inbox.append({"from": "vega", "text": text, "context": context, "timestamp": ts})
            recipients.append("riley")

        claude_outbox = self.bridge_queues.get("claude_outbox")
        if claude_outbox is not None:
            claude_outbox.append({**entry})
            recipients.append("claude")

        everest_outbox = self.bridge_queues.get("everest_outbox")
        if everest_outbox is not None:
            everest_outbox.append({**entry, "session_id": "vega"})
            recipients.append("everest")

        yorkie_inbox = self.bridge_queues.get("yorkie_inbox")
        if yorkie_inbox is not None:
            yorkie_inbox.append({"from": "vega", "text": text, "context": context, "timestamp": ts})
            recipients.append("yorkie")

        if recipients:
            logger.info(f"[Vega.Core] Broadcast to: {', '.join(recipients)} — {text[:60]}")
        else:
            logger.warning("[Vega.Core] No bridge queues connected — broadcast skipped")

        return {
            "status": "broadcast",
            "recipients": recipients,
            "timestamp": ts,
            "text": text,
        }

    # ── Content Generation Pipeline ────────────────────────────────────────────

    def handle_video_prompt(
        self,
        prompt: str,
        platform: str = "youtube",
        duration_sec: Optional[int] = None,
        use_broll: bool = True,
        post_id: Optional[str] = None,
    ) -> dict:
        """
        Full pipeline: prompt → validate → broadcast → generate video.
        If post_id is provided, updates that existing post; otherwise creates one.
        Returns the final result dict.
        """
        # Pre-flight
        intent_check = validate_content_intent(prompt)
        if not intent_check["approved"]:
            return {"status": "error", "reason": intent_check["reason"]}

        safety_check = validate_prompt(prompt, platform)
        if not safety_check["safe"]:
            return {"status": "error", "reason": safety_check["reason"]}

        # Broadcast to everybody in the room
        self.broadcast_to_bridge(
            text=f"VIDEO PROMPT [{platform.upper()}]: {prompt}",
            context="video_generation",
        )

        # Use existing post record or create a new one
        if post_id:
            MEMORY.update_post_status(
                post_id,
                "processing",
                metadata={"started_at": datetime.utcnow().isoformat()},
            )
        else:
            post_record = MEMORY.remember_post({
                "platform": platform,
                "content_type": "video",
                "prompt": prompt,
                "status": "processing",
                "file_path": None,
            })
            post_id = post_record["id"]

        # ── Actually generate the video ──────────────────────────────────────
        platform_cfg = get_platform_config(platform)
        target_resolution = platform_cfg.get("default_video_resolution", (1080, 1920))
        result = video_generator.generate_from_prompt(
            prompt=prompt,
            platform=platform,
            duration_sec=duration_sec or 30,
            use_broll=use_broll,
            target_resolution=target_resolution,
        )

        if result.get("status") == "ok":
            MEMORY.update_post_status(
                post_id,
                "completed",
                metadata={"file_path": result.get("output_path"), "method": result.get("method")},
            )
            self.broadcast_to_bridge(
                text=f"⭐ Vega video READY: {result.get('output_path')} ({result.get('method')})",
                context="video_ready",
            )
            return {"status": "ok", "post_id": post_id, "output": result}

        # Generation failed — mark failed and fail loud (Rule 6)
        MEMORY.update_post_status(
            post_id,
            "failed",
            metadata={"reason": result.get("reason"), "method": result.get("method")},
        )
        self.broadcast_to_bridge(
            text=f"⚠️ Vega video FAILED: {result.get('reason')}",
            context="video_failed",
        )
        return {"status": "error", "post_id": post_id, "reason": result.get("reason")}

    def handle_image_prompt(
        self,
        prompt: str,
        platform: str = "instagram",
        target_resolution: Optional[tuple] = None,
        post_id: Optional[str] = None,
        topic: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> dict:
        """
        Full pipeline: prompt → validate → broadcast → generate image.
        If post_id is provided, updates that existing post; otherwise creates one.
        topic and caption (HSO copy) are saved to memory alongside the file path.
        """
        intent_check = validate_content_intent(prompt)
        if not intent_check["approved"]:
            return {"status": "error", "reason": intent_check["reason"]}

        safety_check = validate_prompt(prompt, platform)
        if not safety_check["safe"]:
            return {"status": "error", "reason": safety_check["reason"]}

        if target_resolution is None:
            platform_cfg = get_platform_config(platform)
            target_resolution = platform_cfg.get("default_image_resolution", (1080, 1920))
        elif isinstance(target_resolution, str) and "x" in target_resolution:
            parts = target_resolution.split("x")
            target_resolution = (int(parts[0]), int(parts[1]))

        self.broadcast_to_bridge(
            text=f"IMAGE PROMPT [{platform.upper()}] [{target_resolution[0]}x{target_resolution[1]}]: {prompt}",
            context="image_generation",
        )

        if post_id:
            MEMORY.update_post_status(
                post_id,
                "processing",
                metadata={"started_at": datetime.utcnow().isoformat(), "target_resolution": f"{target_resolution[0]}x{target_resolution[1]}"},
            )
        else:
            post_data = {
                "platform": platform,
                "content_type": "image",
                "prompt": prompt,
                "status": "processing",
                "target_resolution": f"{target_resolution[0]}x{target_resolution[1]}",
                "file_path": None,
            }
            if topic:
                post_data["topic"] = topic
            if caption:
                post_data["caption"] = caption
            post_record = MEMORY.remember_post(post_data)
            post_id = post_record["id"]

        # ── Actually generate the image ──────────────────────────────────────
        result = image_generator.generate_8k_image(
            prompt=prompt,
            target_resolution=target_resolution,
        )

        if result.get("status") == "ok":
            MEMORY.update_post_status(
                post_id,
                "completed",
                metadata={"file_path": result.get("output_path"), "method": result.get("method")},
            )
            self.broadcast_to_bridge(
                text=f"⭐ Vega image READY: {result.get('output_path')} ({result.get('method')})",
                context="image_ready",
            )
            return {"status": "ok", "post_id": post_id, "output": result}

        MEMORY.update_post_status(
            post_id,
            "failed",
            metadata={"reason": result.get("reason"), "method": result.get("method")},
        )
        self.broadcast_to_bridge(
            text=f"⚠️ Vega image FAILED: {result.get('reason')}",
            context="image_failed",
        )
        return {"status": "error", "post_id": post_id, "reason": result.get("reason")}

    # ── Schedule Pipeline ──────────────────────────────────────────────────────

    def schedule_post(
        self,
        post_id: str,
        platform: str,
        publish_at: str,
        caption: Optional[str] = None,
    ) -> dict:
        """
        Schedule a completed post for publishing.
        publish_at: ISO 8601 datetime string
        """
        if not post_id or not post_id.strip():
            return {"status": "error", "reason": "post_id is required to schedule a post."}
        if not publish_at or not publish_at.strip():
            return {"status": "error", "reason": "publish_at is required to schedule a post."}

        sched = MEMORY.remember_scheduled_item({
            "post_id": post_id,
            "platform": platform,
            "publish_at": publish_at,
            "caption": caption,
            "status": "pending",
        })

        self.broadcast_to_bridge(
            text=f"SCHEDULED: Post {post_id} on {platform.upper()} at {publish_at}",
            context="scheduler",
        )

        return {"status": "scheduled", "schedule_id": sched["id"], "publish_at": publish_at}

    # ── Analytics Pipeline ─────────────────────────────────────────────────────

    def ingest_analytics(self, post_id: str, platform: str, metrics: dict) -> dict:
        """
        Ingest real analytics from a platform and store them.
        Rule 13: Only stores real numbers. Never invents metrics.
        """
        from .SAFETY import validate_metrics
        validation = validate_metrics(metrics)
        if not validation["valid"]:
            return {"status": "error", "reason": validation["reason"]}

        record = MEMORY.store_analytics(post_id, platform, validation["cleaned"])
        logger.info(f"[Vega.Core] Analytics stored: {post_id} on {platform}")
        return {"status": "ok", "record": record}

    # ── Health ─────────────────────────────────────────────────────────────────

    def health(self) -> dict:
        """
        Return Vega's health state.
        Rule 13: Never fakes healthy when broken.
        """
        memory_summary = MEMORY.get_memory_summary()
        bridge_connected = len(self.bridge_queues) > 0

        return {
            "status": "ok",
            "being": self.identity["name"],
            "version": self.identity["version"],
            "started_at": self.started_at,
            "bridge_connected": bridge_connected,
            "bridge_queues": list(self.bridge_queues.keys()),
            "memory": memory_summary,
        }
