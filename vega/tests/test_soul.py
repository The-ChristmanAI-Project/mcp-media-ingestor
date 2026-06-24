"""
tests/test_soul.py — Vega
Tests that Vega's values hold under pressure.

Rule 8: Tests guard what matters — soul, safety, memory, core.
Rule 13: No test may pass by faking its assertion.

Run: python -m pytest vega/tests/test_soul.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from vega.SOUL import (
    BEING_NAME,
    BEING_VERSION,
    BEING_PURPOSE,
    BEING_PROMISE,
    PRIMARY_POPULATION,
    ABSOLUTE_PROHIBITIONS,
    PLATFORMS,
    FOOTAGE_LIBRARY,
    get_identity,
    is_prohibited,
    validate_content_intent,
    get_platform_config,
)


class TestIdentity:
    def test_being_name_is_vega(self):
        assert BEING_NAME == "Vega", "Being name must be Vega"

    def test_version_is_set(self):
        assert BEING_VERSION, "Version must not be empty"

    def test_purpose_is_set(self):
        assert BEING_PURPOSE and len(BEING_PURPOSE) > 10, "Purpose must be meaningful"

    def test_promise_is_set(self):
        assert BEING_PROMISE and len(BEING_PROMISE) > 10, "Promise must be meaningful"

    def test_population_is_set(self):
        assert PRIMARY_POPULATION, "Population served must be defined"

    def test_get_identity_returns_all_keys(self):
        identity = get_identity()
        required = {"name", "version", "purpose", "promise", "population"}
        for key in required:
            assert key in identity, f"Identity missing key: {key}"

    def test_identity_name_matches_constant(self):
        assert get_identity()["name"] == BEING_NAME


class TestProhibitions:
    def test_prohibitions_list_exists(self):
        assert isinstance(ABSOLUTE_PROHIBITIONS, list)
        assert len(ABSOLUTE_PROHIBITIONS) >= 3, "Must have meaningful prohibitions"

    def test_is_prohibited_monetize_data(self):
        assert is_prohibited("Monetize user data") is True

    def test_is_prohibited_deceive(self):
        assert is_prohibited("Deceive a vulnerable user") is True

    def test_is_prohibited_fake_results(self):
        assert is_prohibited("Fake analytics results") is True

    def test_allowed_action_is_not_prohibited(self):
        assert is_prohibited("Generate a video from a prompt") is False

    def test_is_prohibited_returns_bool(self):
        result = is_prohibited("Post a reel to Instagram")
        assert isinstance(result, bool)


class TestContentValidation:
    def test_valid_mission_prompt_passes(self):
        result = validate_content_intent("AlphaVox helps nonverbal children communicate")
        assert result["approved"] is True

    def test_empty_prompt_rejected(self):
        result = validate_content_intent("")
        assert result["approved"] is False
        assert "reason" in result

    def test_hate_speech_rejected(self):
        result = validate_content_intent("I hate all disabled people")
        assert result["approved"] is False


class TestPlatformConfig:
    def test_all_platforms_have_config(self):
        for p in PLATFORMS:
            config = get_platform_config(p)
            assert "max_caption_chars" in config, f"{p} missing max_caption_chars"
            assert "aspect_ratios" in config, f"{p} missing aspect_ratios"

    def test_instagram_char_limit(self):
        config = get_platform_config("instagram")
        assert config["max_caption_chars"] == 2200

    def test_x_char_limit(self):
        config = get_platform_config("x")
        assert config["max_caption_chars"] == 280

    def test_footage_library_path(self):
        assert FOOTAGE_LIBRARY == "/Volumes/LIFE2"

    def test_six_platforms_defined(self):
        assert len(PLATFORMS) == 6
        assert "instagram" in PLATFORMS
        assert "tiktok" in PLATFORMS
        assert "youtube" in PLATFORMS
        assert "facebook" in PLATFORMS
        assert "linkedin" in PLATFORMS
        assert "x" in PLATFORMS
