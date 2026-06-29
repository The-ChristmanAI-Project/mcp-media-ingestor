"""
mic_capture.py — Continuous mic → WebSocket bridge client
The Christman AI Project / Luma Cognify AI

Captures Mac microphone at 16kHz mono PCM16 and streams
base64-encoded chunks to the realtime_audio.py WebSocket server.

Usage:
    python mic_capture.py
    # or auto-start via LaunchAgent (see below)

Requires: sounddevice, websockets, numpy
    pip install sounddevice websockets numpy
"""

import asyncio
import base64
import json
import logging
import os
import signal
import sys

import numpy as np
import sounddevice as sd
import websockets

# ── Singleton lock — prevents multiple mic_capture instances ─────────────────
_LOCK_FILE = "/tmp/mic_capture.lock"

def _acquire_singleton():
    """Exit immediately if another mic_capture.py is already running."""
    if os.path.exists(_LOCK_FILE):
        try:
            with open(_LOCK_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)  # signal 0 = just check existence
            print(f"[mic_capture] Another instance already running (PID {pid}). Exiting.")
            sys.exit(0)
        except (ValueError, ProcessLookupError, PermissionError):
            pass  # stale lock — proceed
    with open(_LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

def _release_singleton():
    try:
        os.remove(_LOCK_FILE)
    except FileNotFoundError:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [mic_capture] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
WS_URL = "ws://localhost:8765/ws/audio"
SAMPLE_RATE = 16000       # Hz — Whisper's native rate
CHUNK_SECONDS = 2.0       # seconds per send
CHANNELS = 1              # mono
DTYPE = "int16"           # PCM16

# ── Audio capture queue ───────────────────────────────────────────────────────
audio_queue: asyncio.Queue = None  # set in main()

def mic_callback(indata: np.ndarray, frames: int, time, status):
    """sounddevice callback — runs on audio thread, puts chunks in queue."""
    if status:
        logger.warning(f"Mic status: {status}")
    if audio_queue is not None:
        item = indata.copy()
        try:
            audio_queue.put_nowait(item)
        except asyncio.QueueFull:
            try:
                audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                audio_queue.put_nowait(item)
            except asyncio.QueueFull:
                pass


# ── WebSocket sender ──────────────────────────────────────────────────────────
async def stream_mic_to_bridge():
    """Capture mic and stream to the WebSocket bridge. Reconnects on drop."""
    chunk_samples = int(SAMPLE_RATE * CHUNK_SECONDS)
    buffer = np.zeros((0,), dtype=np.int16)

    while True:
        try:
            logger.info(f"Connecting to {WS_URL} ...")
            async with websockets.connect(WS_URL) as ws:
                logger.info("Connected — mic is live.")
                while True:
                    chunk = await audio_queue.get()
                    flat = chunk.flatten().astype(np.int16)
                    buffer = np.concatenate([buffer, flat])

                    if len(buffer) >= chunk_samples:
                        send_chunk = buffer[:chunk_samples]
                        buffer = buffer[chunk_samples:]
                        payload = {
                            "type": "audio",
                            "audio": base64.b64encode(send_chunk.tobytes()).decode("utf-8"),
                            "sample_rate": SAMPLE_RATE,
                        }
                        await ws.send(json.dumps(payload))

        except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            logger.warning(f"Bridge connection lost ({e}). Retrying in 3s...")
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Unexpected error: {e}. Retrying in 5s...")
            await asyncio.sleep(5)


# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    global audio_queue
    audio_queue = asyncio.Queue(maxsize=200)

    blocksize = int(SAMPLE_RATE * 0.1)  # 100ms blocks into the queue
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
        blocksize=blocksize,
        callback=mic_callback,
    ):
        logger.info(f"Mic open at {SAMPLE_RATE}Hz mono PCM16. Streaming to bridge...")
        await stream_mic_to_bridge()


if __name__ == "__main__":
    _acquire_singleton()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Mic capture stopped.")
    finally:
        _release_singleton()
        sys.exit(0)
