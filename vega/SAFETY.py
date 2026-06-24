"""
SAFETY.py — Vega
Brand safety, content validation, fail-loud handlers.
Rule 6: Fail loud. Rule 8: Test what matters. Rule 12: Security is mandatory.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply. Rule 13 is gospel.
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vega.safety")

# Brand safety — content that must never be published
BRAND_SAFETY_BLOCKED = [
    "violence",
    "hate speech",
    "explicit content",
    "misinformation",
    "fabricated statistics",
    "fake news",
    "misleading claims",
]

# Platform-specific content policies (the ones we enforce locally)
PLATFORM_POLICIES = {
    "tiktok": ["no nudity", "no graphic violence", "no misinformation"],
    "instagram": ["no nudity", "no graphic violence", "no spam"],
    "youtube": ["no sexual content", "no violent extremism", "no spam"],
    "facebook": ["no hate speech", "no graphic violence", "no nudity"],
    "linkedin": ["no inappropriate content", "professional tone required"],
    "x": ["no targeted harassment", "no synthetic media without disclosure"],
}


def validate_prompt(prompt: str, platform: Optional[str] = None) -> dict:
    """
    Validate a content prompt before generation begins.
    Fails loud if the prompt would produce unsafe content. (Rule 6)

    Returns:
        {"safe": bool, "reason": str, "blocked_term": Optional[str]}
    """
    if not prompt or not prompt.strip():
        return {"safe": False, "reason": "Empty prompt.", "blocked_term": None}

    prompt_lower = prompt.lower()

    for term in BRAND_SAFETY_BLOCKED:
        if term in prompt_lower:
            logger.warning(f"[Vega.Safety] Blocked term in prompt: '{term}'")
            return {
                "safe": False,
                "reason": f"Prompt contains blocked term: '{term}'. Vega enforces brand safety.",
                "blocked_term": term,
            }

    if platform and platform.lower() in PLATFORM_POLICIES:
        policies = PLATFORM_POLICIES[platform.lower()]
        for policy in policies:
            # Basic keyword check — real implementation would use a classifier
            policy_lower = policy.lower()
            if any(word in prompt_lower for word in policy_lower.split()
                   if len(word) > 4):
                logger.warning(f"[Vega.Safety] Platform policy flag: {policy}")
                return {
                    "safe": False,
                    "reason": f"Prompt may violate {platform} policy: {policy}",
                    "blocked_term": policy,
                }

    return {"safe": True, "reason": "Prompt passed safety validation.", "blocked_term": None}


def validate_file_path(path: str, expected_base: Optional[str] = None) -> dict:
    """
    Validate that a file path is safe to read/write.
    Prevents path traversal attacks. (Rule 12)

    Returns:
        {"safe": bool, "reason": str}
    """
    try:
        resolved = Path(path).resolve()
    except Exception as e:
        return {"safe": False, "reason": f"Path resolution failed: {e}"}

    # Prevent path traversal outside expected base
    if expected_base:
        base_resolved = Path(expected_base).resolve()
        try:
            resolved.relative_to(base_resolved)
        except ValueError:
            logger.error(f"[Vega.Safety] Path traversal attempt: {path}")
            return {
                "safe": False,
                "reason": f"Path '{path}' is outside allowed base '{expected_base}'",
            }

    return {"safe": True, "reason": "Path is safe."}


def validate_output(output: dict) -> bool:
    """
    Validate output before returning to the bridge or dashboard.
    Rule 13: Never let a fabricated response reach users.

    Returns True if output is valid.
    """
    required_keys = {"status"}
    for key in required_keys:
        if key not in output:
            logger.error(f"[Vega.Safety] Output missing required key: '{key}'")
            return False

    if output.get("status") not in {"ok", "error", "pending", "scheduled",
                                     "published", "cancelled", "processing"}:
        logger.error(f"[Vega.Safety] Unknown status value: {output.get('status')}")
        return False

    return True


def validate_metrics(metrics: dict) -> dict:
    """
    Validate analytics metrics before storing.
    Rule 13: No fabricated engagement numbers. Ever.

    All numeric values must be non-negative integers or floats.
    Returns:
        {"valid": bool, "reason": str, "cleaned": dict}
    """
    cleaned = {}
    for key, value in metrics.items():
        if not isinstance(value, (int, float)):
            return {
                "valid": False,
                "reason": f"Metric '{key}' is not a number: {type(value).__name__}. "
                          "Vega never fabricates analytics. (Rule 13)",
                "cleaned": {},
            }
        if value < 0:
            return {
                "valid": False,
                "reason": f"Metric '{key}' is negative ({value}). "
                          "Engagement counts cannot be negative.",
                "cleaned": {},
            }
        cleaned[key] = int(value) if isinstance(value, float) and value == int(value) else value

    return {"valid": True, "reason": "Metrics validated.", "cleaned": cleaned}


def check_env_vars(required_vars: list[str]) -> dict:
    """
    Check that required environment variables are set.
    Rule 12: No secrets in source. All secrets come from environment.

    Returns:
        {"ok": bool, "missing": list[str]}
    """
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        logger.warning(f"[Vega.Safety] Missing env vars: {missing}")
        return {"ok": False, "missing": missing}
    return {"ok": True, "missing": []}


def content_size_check(file_path: str, max_mb: float = 500.0) -> dict:
    """
    Check that a generated file is within size limits before upload.
    Returns:
        {"ok": bool, "size_mb": float, "reason": str}
    """
    p = Path(file_path)
    if not p.exists():
        return {"ok": False, "size_mb": 0, "reason": f"File not found: {file_path}"}

    size_mb = p.stat().st_size / (1024 * 1024)
    if size_mb > max_mb:
        return {
            "ok": False,
            "size_mb": round(size_mb, 2),
            "reason": f"File size {size_mb:.1f}MB exceeds limit of {max_mb}MB",
        }

    return {"ok": True, "size_mb": round(size_mb, 2), "reason": "Size OK."}
