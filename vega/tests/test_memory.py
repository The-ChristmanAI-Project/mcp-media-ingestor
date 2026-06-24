"""
tests/test_memory.py — Vega
Memory persists and retrieves correctly. (Rule 13: never fabricate memory)

Run: python -m pytest vega/tests/test_memory.py -v
"""

import sys
import os
import json
import shutil
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest


@pytest.fixture
def mem(tmp_path, monkeypatch):
    """VegaMemory pointed at a temp directory so we don't touch real data."""
    from vega import MEMORY as M
    monkeypatch.setattr(M, "DATA_DIR", tmp_path)
    m = M.VegaMemory()
    m.data_dir = tmp_path
    return m


class TestPostMemory:
    def test_remember_post_returns_dict(self, mem):
        result = mem.remember_post({
            "post_id": "test_001",
            "platform": "instagram",
            "content_type": "image",
            "prompt": "AlphaVox helps kids speak",
        })
        assert isinstance(result, dict)
        assert result.get("status") == "stored"

    def test_recall_post_by_platform(self, mem):
        mem.remember_post({"post_id": "ig_001", "platform": "instagram", "content_type": "video"})
        mem.remember_post({"post_id": "tt_001", "platform": "tiktok", "content_type": "video"})
        posts = mem.recall_posts(platform="instagram")
        assert all(p["platform"] == "instagram" for p in posts)

    def test_recall_returns_list(self, mem):
        result = mem.recall_posts()
        assert isinstance(result, list)

    def test_recall_empty_when_no_posts(self, mem):
        result = mem.recall_posts()
        assert result == []

    def test_update_post_status(self, mem):
        mem.remember_post({"post_id": "up_001", "platform": "youtube", "content_type": "video"})
        result = mem.update_post_status("up_001", "published", {"platform_post_id": "YT123"})
        assert result.get("status") == "updated"

    def test_post_persistence(self, mem):
        mem.remember_post({"post_id": "persist_001", "platform": "facebook"})
        # Re-instantiate to check persistence
        from vega.MEMORY import VegaMemory
        mem2 = VegaMemory()
        mem2.data_dir = mem.data_dir
        posts = mem2.recall_posts()
        assert any(p.get("post_id") == "persist_001" for p in posts)


class TestAnalyticsMemory:
    def test_store_and_recall_analytics(self, mem):
        mem.remember_post({"post_id": "ana_001", "platform": "instagram"})
        mem.store_analytics("ana_001", "instagram", {"views": 5000, "likes": 200})
        records = mem.recall_analytics("ana_001", platform="instagram")
        assert len(records) >= 1
        assert records[0]["metrics"].get("views") == 5000

    def test_analytics_returns_list(self, mem):
        result = mem.recall_analytics("nonexistent_post")
        assert isinstance(result, list)

    def test_analytics_never_fabricates(self, mem):
        """Rule 13: No data → empty list, not invented data."""
        result = mem.recall_analytics("ghost_post_xyz")
        assert result == []


class TestScheduleMemory:
    def test_remember_scheduled_item(self, mem):
        result = mem.remember_scheduled_item({
            "post_id": "sched_001",
            "platform": "tiktok",
            "publish_at": "2026-07-01T12:00:00Z",
            "caption": "Test post",
        })
        assert result.get("status") == "stored"

    def test_recall_schedule_pending(self, mem):
        mem.remember_scheduled_item({
            "post_id": "sched_002",
            "platform": "instagram",
            "publish_at": "2026-07-02T10:00:00Z",
            "status": "pending",
        })
        items = mem.recall_schedule(pending_only=True)
        assert any(i.get("post_id") == "sched_002" for i in items)

    def test_schedule_returns_list(self, mem):
        assert isinstance(mem.recall_schedule(), list)


class TestMemorySummary:
    def test_summary_returns_dict(self, mem):
        result = mem.get_memory_summary()
        assert isinstance(result, dict)

    def test_summary_has_counts(self, mem):
        mem.remember_post({"post_id": "sum_001", "platform": "linkedin"})
        summary = mem.get_memory_summary()
        assert "total_posts" in summary
        assert summary["total_posts"] >= 1
