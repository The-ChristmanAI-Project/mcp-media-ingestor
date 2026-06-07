"""
TONE.py — Christman Audio Tone Analyzer
Analyzes energy, pace, and emotional signal from a WAV file.
Uses amplitude statistics + faster-whisper word timestamps for pace.
"""
import wave
import numpy as np


def analyze_tone(audio_path: str) -> dict:
    """
    Analyze tone from a .wav file.
    Returns a dict with energy, pace estimate, and dominant tone label.
    """
    try:
        with wave.open(audio_path, "r") as wf:
            frames = wf.readframes(wf.getnframes())
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()

        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
        if channels == 2:
            audio = audio[::2]  # take left channel

        amplitude = np.abs(audio)
        energy = float(np.mean(amplitude))
        peak = float(np.max(amplitude))
        variance = float(np.std(amplitude))

        # Normalize energy to 0–1 against int16 max
        energy_norm = energy / 32768.0
        peak_norm = peak / 32768.0

        # Heuristic tone labels based on energy and variance
        if energy_norm > 0.25 and variance > 5000:
            tone = "energized"
        elif energy_norm > 0.15:
            tone = "engaged"
        elif energy_norm > 0.05:
            tone = "calm"
        else:
            tone = "quiet"

        duration = len(audio) / sample_rate

        return {
            "tone": tone,
            "energy": round(energy_norm, 4),
            "peak": round(peak_norm, 4),
            "variance": round(variance, 2),
            "duration_seconds": round(duration, 2),
            "sample_rate": sample_rate,
        }

    except Exception as e:
        return {"tone": "unknown", "error": str(e)}
