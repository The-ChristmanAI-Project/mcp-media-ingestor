"""
voice/narrator.py — Vega
Script reading and voiceover generation via Christman Sound SDK.

This calls Everett's SDK. That's it.
Rule 13: Never claim voiceover was generated if no file was written.
Rule 6:  Fail loud if the SDK isn't available.
Rule 15: No paid APIs. No cloud TTS. Not ever.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply. Rule 13 is gospel.
"""

import logging
import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vega.voice.narrator")

AUDIO_OUTPUT_DIR  = Path(__file__).resolve().parents[2] / "vega_output" / "audio"
CHRISTMAN_SDK     = Path("/Users/EverettN/Christman-Sound")


def _ensure_audio_dir() -> Path:
    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return AUDIO_OUTPUT_DIR


def generate_voiceover(
    script: str,
    output_filename: Optional[str] = None,
    tone: str = "warm",
    voice_id: Optional[str] = None,
) -> dict:
    """
    Generate a voiceover using the Christman Sound SDK.

    Returns:
        {"status": "ok", "path": str, "engine": "christman_sound", "duration_estimate_sec": float}
        {"status": "error", "reason": str}
    """
    if not script or not script.strip():
        return {"status": "error", "reason": "Script is empty."}

    script = script.strip()
    filename = output_filename or f"vega_narration_{uuid.uuid4().hex[:8]}.wav"
    out_path = _ensure_audio_dir() / filename

    sdk = str(CHRISTMAN_SDK)
    if sdk not in sys.path:
        sys.path.insert(0, sdk)

    try:
        from core import synthesize_speech, resolve_voice_params
    except ImportError as e:
        logger.error(f"[Vega.Narrator] Christman Sound SDK not found at {CHRISTMAN_SDK}: {e}")
        return {"status": "error", "reason": f"Christman Sound SDK not found: {e}"}

    # Map Vega tone → Christman emotion
    tone_map = {
        "warm":        ("neutral", 0.0),
        "calm":        ("neutral", -0.2),
        "urgent":      ("emphasis", 0.4),
        "firm":        ("emphasis", 0.2),
        "celebratory": ("happy", 0.5),
    }
    emotion, exaggeration = tone_map.get(tone, ("neutral", 0.0))

    voice_params = resolve_voice_params(
        tone_score=72.0,
        dominant_emotion=emotion,
        exaggeration=exaggeration,
    )

    result_path = synthesize_speech(
        text=script,
        voice_params=voice_params,
    )

    if result_path and Path(result_path).exists() and Path(result_path).stat().st_size > 100:
        wav_path = out_path.with_suffix(".wav")
        shutil.copy2(str(result_path), str(wav_path))
        logger.info(f"[Vega.Narrator] ✅ Christman Sound → {wav_path}")
        return {
            "status": "ok",
            "engine": "christman_sound",
            "path": str(wav_path),
            "duration_estimate_sec": _estimate_duration(script),
        }

    reason = (
        "Christman Sound returned no audio. "
        "Check that CHRISTMAN_REFERENCE_AUDIO is set and the reference WAV exists."
    )
    logger.error(f"[Vega.Narrator] {reason}")
    return {"status": "error", "reason": reason}


def _estimate_duration(script: str, words_per_minute: int = 150) -> float:
    return round((len(script.split()) / words_per_minute) * 60, 1)
