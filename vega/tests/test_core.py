"""
tests/test_core.py — Vega
Core functionality is real, not imagined. (Rule 1, Rule 8, Rule 13)

Run: python -m pytest vega/tests/test_core.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def bridge_queues():
    return {
        "riley_inbox":   [],
        "claude_outbox": [],
        "everest_outbox": [],
        "yorkie_inbox":  [],
    }


@pytest.fixture
def core(bridge_queues):
    from vega.CORE import VegaCore
    return VegaCore(bridge_queues=bridge_queues)


class TestVegaCoreInit:
    def test_core_initializes(self, core):
        assert core is not None

    def test_core_without_queues(self):
        from vega.CORE import VegaCore
        c = VegaCore()
        assert c is not None

    def test_health_returns_dict(self, core):
        result = core.health()
        assert isinstance(result, dict)
        assert "status" in result

    def test_health_never_lies(self, core):
        """Rule 13: health() returns real status."""
        result = core.health()
        assert result["status"] in ("ok", "degraded", "error", "unavailable")


class TestBroadcast:
    def test_broadcast_sends_to_all_queues(self, core, bridge_queues):
        core.broadcast_to_bridge("Test broadcast from Vega", context="test")
        assert len(bridge_queues["riley_inbox"]) >= 1
        assert len(bridge_queues["claude_outbox"]) >= 1
        assert len(bridge_queues["everest_outbox"]) >= 1
        assert len(bridge_queues["yorkie_inbox"]) >= 1

    def test_broadcast_returns_dict(self, core):
        result = core.broadcast_to_bridge("Hello bridge")
        assert isinstance(result, dict)

    def test_broadcast_message_in_queue(self, core, bridge_queues):
        core.broadcast_to_bridge("UNIQUE_TEST_MESSAGE_XYZ")
        all_texts = [
            e.get("text", "") for e in
            bridge_queues["riley_inbox"] +
            bridge_queues["claude_outbox"] +
            bridge_queues["everest_outbox"] +
            bridge_queues["yorkie_inbox"]
        ]
        assert any("UNIQUE_TEST_MESSAGE_XYZ" in t for t in all_texts)

    def test_broadcast_without_queues_doesnt_crash(self):
        from vega.CORE import VegaCore
        c = VegaCore()
        result = c.broadcast_to_bridge("No queues attached")
        assert isinstance(result, dict)


class TestVideoPromptHandling:
    def test_empty_prompt_rejected(self, core):
        result = core.handle_video_prompt("", "instagram", 15, True)
        assert result["status"] == "error"
        assert "reason" in result

    def test_returns_post_id(self, core):
        result = core.handle_video_prompt(
            "AlphaVox demo reel for Instagram", "instagram", 15, False
        )
        assert "post_id" in result

    def test_video_broadcasts_to_bridge(self, core, bridge_queues):
        core.handle_video_prompt("Mission reel", "tiktok", 10, False)
        all_entries = (
            bridge_queues["riley_inbox"] +
            bridge_queues["claude_outbox"] +
            bridge_queues["everest_outbox"] +
            bridge_queues["yorkie_inbox"]
        )
        assert len(all_entries) > 0


class TestImagePromptHandling:
    def test_empty_prompt_rejected(self, core):
        result = core.handle_image_prompt("", "instagram", "7680x4320")
        assert result["status"] == "error"

    def test_returns_post_id(self, core):
        result = core.handle_image_prompt(
            "8K poster for Aegis AI child protection", "linkedin", "7680x4320"
        )
        assert "post_id" in result

    def test_image_broadcasts_to_bridge(self, core, bridge_queues):
        core.handle_image_prompt("Inspirational image", "facebook", "3840x2160")
        all_entries = (
            bridge_queues["riley_inbox"] +
            bridge_queues["claude_outbox"] +
            bridge_queues["everest_outbox"] +
            bridge_queues["yorkie_inbox"]
        )
        assert len(all_entries) > 0


class TestSchedulePost:
    def test_missing_fields_rejected(self, core):
        result = core.schedule_post("", "instagram", "", "")
        assert result["status"] == "error"

    def test_schedule_returns_dict(self, core):
        result = core.schedule_post(
            "post_001", "instagram", "2099-01-01T12:00:00Z", "Test caption"
        )
        assert isinstance(result, dict)
        assert "status" in result


class TestAnalyticsIngest:
    def test_empty_metrics_rejected(self, core):
        result = core.ingest_analytics("post_001", "instagram", {})
        assert result["status"] == "error"

    def test_negative_metrics_rejected(self, core):
        """Rule 13: Negative analytics numbers are impossible — reject them."""
        result = core.ingest_analytics("post_001", "instagram", {"views": -500})
        assert result["status"] == "error"

    def test_valid_metrics_accepted(self, core):
        result = core.ingest_analytics("post_001", "instagram", {
            "views": 10000, "likes": 500, "comments": 30
        })
        assert result["status"] in ("stored", "ok")
