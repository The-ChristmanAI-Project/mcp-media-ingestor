"""
voice/narrator.py — Vega
Script reading and voiceover generation.

Strategy (in order):
  1. ElevenLabs API (highest quality, if ELEVENLABS_API_KEY is set)
  2. edge-tts (Microsoft Edge TTS — free, high quality, offline-capable)
  3. pyttsx3 (fully offline fallback, lower quality)

All strategies produce a real .mp3 or .wav file in vega_output/audio/.
Rule 13: Never claim voiceover was generated if no file was written.
Rule 1:  The audio file must actually exist and be playable.
Rule 6:  If all strategies fail, raises with a clear explanation.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply. Rule 13 is gospel.
"""

import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vega.voice.narrator")

AUDIO_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "vega_output" / "audio"

# ElevenLabs voice IDs for Christman project — can be overridden via env
DEFAULT_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # "Bella"

# Edge-TTS voice (Microsoft Neural)
DEFAULT_EDGE_VOICE = "en-US-AriaNeural"

# Tone → edge-tts prosody rate
TONE_RATE = {
    "calm": "-10%",
    "warm": "0%",
    "urgent": "+15%",
    "firm": "+5%",
    "celebratory": "+10%",
}


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
    Convert a script (text) to an audio file.

    Args:
        script:          The text to narrate. Can be a full script or caption.
        output_filename: e.g. "intro_reel.mp3". Auto-generated if None.
        tone:            One of: calm, warm, urgent, firm, celebratory
        voice_id:        ElevenLabs voice ID override (optional)

    Returns:
        {
            "status": "ok",
            "path": "/absolute/path/to/audio.mp3",
            "engine": "elevenlabs" | "edge-tts" | "pyttsx3",
            "duration_estimate_sec": <float>
        }
    """
    if not script or not script.strip():
        return {"status": "error", "reason": "Script is empty. Nothing to narrate."}

    script = script.strip()
    filename = output_filename or f"vega_narration_{uuid.uuid4().hex[:8]}.mp3"
    out_path = _ensure_audio_dir() / filename

    # Strategy 1: ElevenLabs
    if os.environ.get("ELEVENLABS_API_KEY"):
        result = _generate_elevenlabs(script, out_path, voice_id or DEFAULT_VOICE_ID, tone)
        if result.get("status") == "ok":
            return result
        logger.warning(f"[Vega.Narrator] ElevenLabs failed: {result.get('reason')} — trying edge-tts")

    # Strategy 2: edge-tts (async, produces .mp3)
    result = _generate_edge_tts(script, out_path, tone)
    if result.get("status") == "ok":
        return result
    logger.warning(f"[Vega.Narrator] edge-tts failed: {result.get('reason')} — trying pyttsx3")

    # Strategy 3: pyttsx3 offline (produces .wav)
    wav_path = out_path.with_suffix(".wav")
    result = _generate_pyttsx3(script, wav_path)
    if result.get("status") == "ok":
        return result

    # Rule 6: all strategies failed — fail loud
    return {
        "status": "error",
        "reason": (
            "All voiceover engines failed. "
            "Set ELEVENLABS_API_KEY for best quality, "
            "or install edge-tts: pip install edge-tts"
        ),
    }


def read_script_file(
    script_path: str,
    output_filename: Optional[str] = None,
    tone: str = "warm",
    voice_id: Optional[str] = None,
) -> dict:
    """
    Read a script FILE and generate voiceover.
    Accepts .txt, .md, or any plain-text file.

    Rule 13: If the file doesn't exist, says so — doesn't invent content.
    """
    p = Path(script_path)
    if not p.exists():
        return {"status": "error", "reason": f"Script file not found: {script_path}"}
    if not p.is_file():
        return {"status": "error", "reason": f"Path is not a file: {script_path}"}

    try:
        script = p.read_text(encoding="utf-8").strip()
    except Exception as e:
        return {"status": "error", "reason": f"Could not read script file: {e}"}

    if not script:
        return {"status": "error", "reason": f"Script file is empty: {script_path}"}

    logger.info(f"[Vega.Narrator] Reading script from {script_path} ({len(script)} chars)")

    if output_filename is None:
        output_filename = p.stem + "_narration.mp3"

    return generate_voiceover(script, output_filename=output_filename, tone=tone, voice_id=voice_id)


def estimate_duration(script: str, words_per_minute: int = 150) -> float:
    """
    Estimate narration duration in seconds.
    Standard English speech is ~130-160 WPM. Default 150.
    """
    word_count = len(script.split())
    return round((word_count / words_per_minute) * 60, 1)


# ── Strategy 1: ElevenLabs ────────────────────────────────────────────────────

def _generate_elevenlabs(script: str, out_path: Path, voice_id: str, tone: str) -> dict:
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import save

        client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

        # Map tone to stability/similarity_boost
        voice_settings = {
            "calm":        {"stability": 0.80, "similarity_boost": 0.75},
            "warm":        {"stability": 0.70, "similarity_boost": 0.80},
            "urgent":      {"stability": 0.45, "similarity_boost": 0.85},
            "firm":        {"stability": 0.65, "similarity_boost": 0.80},
            "celebratory": {"stability": 0.50, "similarity_boost": 0.90},
        }.get(tone, {"stability": 0.70, "similarity_boost": 0.80})

        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=script,
            model_id="eleven_multilingual_v2",
            voice_settings=voice_settings,
        )

        save(audio, str(out_path))

        if not out_path.exists() or out_path.stat().st_size < 100:
            return {"status": "error", "reason": "ElevenLabs returned empty audio file"}

        logger.info(f"[Vega.Narrator] ElevenLabs → {out_path}")
        return {
            "status": "ok",
            "engine": "elevenlabs",
            "path": str(out_path),
            "duration_estimate_sec": estimate_duration(script),
        }

    except ImportError:
        return {"status": "error", "reason": "elevenlabs not installed. pip install elevenlabs"}
    except Exception as e:
        return {"status": "error", "reason": f"ElevenLabs API error: {e}"}


# ── Strategy 2: edge-tts ──────────────────────────────────────────────────────

def _generate_edge_tts(script: str, out_path: Path, tone: str) -> dict:
    try:
        import edge_tts

        rate = TONE_RATE.get(tone, "0%")

        async def _run():
            communicate = edge_tts.Communicate(
                text=script,
                voice=DEFAULT_EDGE_VOICE,
                rate=rate,
            )
            await communicate.save(str(out_path))

        # Run in event loop — handle both fresh loops and running loops
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _run())
                    future.result(timeout=60)
            else:
                loop.run_until_complete(_run())
        except RuntimeError:
            asyncio.run(_run())

        if not out_path.exists() or out_path.stat().st_size < 100:
            return {"status": "error", "reason": "edge-tts returned empty audio file"}

        logger.info(f"[Vega.Narrator] edge-tts → {out_path}")
        return {
            "status": "ok",
            "engine": "edge-tts",
            "path": str(out_path),
            "duration_estimate_sec": estimate_duration(script),
        }

    except ImportError:
        return {"status": "error", "reason": "edge-tts not installed. pip install edge-tts"}
    except Exception as e:
        return {"status": "error", "reason": f"edge-tts error: {e}"}


# ── Strategy 3: pyttsx3 offline ───────────────────────────────────────────────

def _generate_pyttsx3(script: str, out_path: Path) -> dict:
    try:
        import pyttsx3

        engine = pyttsx3.init()
        engine.setProperty("rate", 150)   # words per minute
        engine.setProperty("volume", 0.9)

        # Try to pick a natural-sounding voice if available
        voices = engine.getProperty("voices")
        for voice in voices:
            if "zira" in voice.name.lower() or "david" in voice.name.lower():
                engine.setProperty("voice", voice.id)
                break

        engine.save_to_file(script, str(out_path))
        engine.runAndWait()

        if not out_path.exists() or out_path.stat().st_size < 100:
            return {"status": "error", "reason": "pyttsx3 produced empty audio file"}

        logger.info(f"[Vega.Narrator] pyttsx3 (offline) → {out_path}")
        return {
            "status": "ok",
            "engine": "pyttsx3",
            "path": str(out_path),
            "duration_estimate_sec": estimate_duration(script),
        }

    except ImportError:
        return {"status": "error", "reason": "pyttsx3 not installed. pip install pyttsx3"}
    except Exception as e:
        return {"status": "error", "reason": f"pyttsx3 error: {e}"}
