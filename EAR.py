"""
EAR.py — Christman Live Audio Capture
Records from the default microphone and returns a path to the saved WAV file.
"""
import os
import tempfile
import wave
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"


def listen(max_duration: float = 6.0) -> str:
    """
    Record up to max_duration seconds from the default mic.
    Returns the absolute path to a temporary .wav file.
    """
    samples = int(SAMPLE_RATE * max_duration)
    audio = sd.rec(samples, samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE)
    sd.wait()

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "w") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    return tmp.name
