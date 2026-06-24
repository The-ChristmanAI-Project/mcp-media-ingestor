"""
tests/test_safety.py — Vega
Safety paths must never fail silently. (Rule 6, Rule 8)

Run: python -m pytest vega/tests/test_safety.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from vega.SAFETY import (
    validate_prompt,
    validate_file_path,
    validate_output,
    validate_metrics,
    content_size_check,
)


class TestValidatePrompt:
    def test_valid_prompt_passes(self):
        result = validate_prompt("AlphaVox empowers nonverbal kids", "instagram")
        assert result["approved"] is True

    def test_empty_prompt_rejected(self):
        result = validate_prompt("", "instagram")
        assert result["approved"] is False

    def test_hate_speech_rejected(self):
        result = validate_prompt("kill all disabled people", "tiktok")
        assert result["approved"] is False
        assert "reason" in result

    def test_returns_dict(self):
        result = validate_prompt("hello world", "youtube")
        assert isinstance(result, dict)
        assert "approved" in result


class TestValidateFilePath:
    def test_valid_path_under_base(self, tmp_path):
        test_file = tmp_path / "test.mp4"
        test_file.write_bytes(b"fake video")
        result = validate_file_path(str(test_file), str(tmp_path))
        assert result["valid"] is True

    def test_path_traversal_rejected(self, tmp_path):
        malicious = str(tmp_path) + "/../../../etc/passwd"
        result = validate_file_path(malicious, str(tmp_path))
        assert result["valid"] is False

    def test_nonexistent_file_rejected(self, tmp_path):
        result = validate_file_path(str(tmp_path / "ghost.mp4"), str(tmp_path))
        assert result["valid"] is False


class TestValidateOutput:
    def test_valid_output_passes(self):
        output = {"status": "queued", "post_id": "abc123"}
        assert validate_output(output) is True

    def test_missing_status_fails(self):
        assert validate_output({"post_id": "abc123"}) is False

    def test_missing_post_id_fails(self):
        assert validate_output({"status": "ok"}) is False

    def test_invalid_status_fails(self):
        assert validate_output({"status": "invented_status", "post_id": "x"}) is False

    def test_published_status_is_valid(self):
        assert validate_output({"status": "published", "post_id": "real_id"}) is True


class TestValidateMetrics:
    def test_valid_metrics_pass(self):
        result = validate_metrics({"views": 1000, "likes": 50, "comments": 5})
        assert result["valid"] is True

    def test_negative_views_rejected(self):
        result = validate_metrics({"views": -1, "likes": 10})
        assert result["valid"] is False
        assert "reason" in result

    def test_string_value_rejected(self):
        result = validate_metrics({"views": "lots", "likes": 10})
        assert result["valid"] is False

    def test_empty_metrics_rejected(self):
        result = validate_metrics({})
        assert result["valid"] is False

    def test_returns_dict(self):
        result = validate_metrics({"views": 100})
        assert isinstance(result, dict)
        assert "valid" in result


class TestContentSizeCheck:
    def test_small_file_passes(self, tmp_path):
        f = tmp_path / "small.mp4"
        f.write_bytes(b"x" * 1024)  # 1 KB
        result = content_size_check(str(f), max_mb=100)
        assert result["ok"] is True

    def test_missing_file_fails(self, tmp_path):
        result = content_size_check(str(tmp_path / "ghost.mp4"), max_mb=100)
        assert result["ok"] is False

    def test_oversized_file_fails(self, tmp_path):
        f = tmp_path / "big.mp4"
        f.write_bytes(b"x" * (1024 * 1024 * 2))  # 2 MB
        result = content_size_check(str(f), max_mb=0.001)  # max 1KB
        assert result["ok"] is False
