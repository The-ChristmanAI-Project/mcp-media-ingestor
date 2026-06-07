"""
SPEAK.py — Christman Voice Output
Speaks text aloud using the macOS `say` command.
Supports emotion-mapped voice rate and pitch modifiers.
"""
import subprocess

# Emotion → macOS say flags
EMOTION_MAP = {
    "neutral":   {"rate": 185, "voice": "Alex"},
    "warm":      {"rate": 175, "voice": "Alex"},
    "urgent":    {"rate": 210, "voice": "Alex"},
    "calm":      {"rate": 160, "voice": "Alex"},
    "excited":   {"rate": 220, "voice": "Alex"},
    "sad":       {"rate": 155, "voice": "Alex"},
}


def speak(text: str, emotion: str = "neutral") -> dict:
    """
    Speak text aloud using macOS say.
    Returns {"engine": "macOS-say", "status": "ok"} or {"engine": ..., "status": "error", "detail": ...}
    """
    params = EMOTION_MAP.get(emotion, EMOTION_MAP["neutral"])
    cmd = [
        "say",
        "-v", params["voice"],
        "-r", str(params["rate"]),
        text
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode == 0:
            return {"engine": "macOS-say", "status": "ok", "emotion": emotion}
        else:
            return {
                "engine": "macOS-say",
                "status": "error",
                "detail": result.stderr.decode().strip()
            }
    except subprocess.TimeoutExpired:
        return {"engine": "macOS-say", "status": "error", "detail": "timeout"}
    except Exception as e:
        return {"engine": "macOS-say", "status": "error", "detail": str(e)}
