"""
vision_capture.py — Continuous camera/screen → WebSocket bridge client (Total Vision)
The Christman AI Project / Luma Cognify AI

Captures live video frames (webcam or screen) via ffmpeg and streams
base64-encoded JPEGs to the main.py bridge at /ws/video.

This provides the "total vision" symmetric to the live audio hearing pipeline.

Usage:
    python vision_capture.py                # default webcam
    python vision_capture.py screen         # macOS screen capture
    # or set SOURCE=screen ; FPS=2

Requires: ffmpeg in PATH (already needed for the project).
On macOS: uses avfoundation. Adjust device index if needed (0=webcam, 1=screen usually).

The bridge (main.py) will make frames available as ImageContent to Claude
and other consumers via get_current_view() and /vision/latest.
"""

import asyncio
import base64
import json
import logging
import os
import signal
import subprocess
import sys
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [vision_capture] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
WS_URL = "ws://localhost:8765/ws/video"
FPS = float(os.getenv("FPS", "2.0"))          # low rate to protect context / bandwidth
SOURCE = os.getenv("SOURCE", sys.argv[1] if len(sys.argv) > 1 else "webcam")

# macOS avfoundation device selection (adjust for your machine)
# "0" = first video input (usually FaceTime / webcam)
# "1" or "1:none" often screen / capture card
if SOURCE.lower() in ("screen", "desktop", "capture"):
    VIDEO_INPUT = "1:none"   # common for screen on mac
    RESOLUTION = os.getenv("RES", "1280x720")
else:
    VIDEO_INPUT = "0"        # webcam
    RESOLUTION = os.getenv("RES", "640x480")

# ── Helpers ───────────────────────────────────────────────────────────────────

def build_ffmpeg_cmd() -> list[str]:
    """Build ffmpeg command for mjpeg pipe. Works on macOS; adapt for linux/windows."""
    # -f avfoundation on mac. For other OS use v4l2 / dshow etc.
    return [
        "ffmpeg",
        "-f", "avfoundation",
        "-framerate", str(FPS),
        "-video_size", RESOLUTION,
        "-i", VIDEO_INPUT,
        "-f", "mjpeg",
        "-q:v", "7",           # quality (lower number = better, ~5-8 reasonable)
        "-",                   # output to stdout (pipe)
    ]


async def stream_frames_to_bridge(ws):
    """Run ffmpeg, parse mjpeg stream into individual JPEGs, send as base64 frames."""
    cmd = build_ffmpeg_cmd()
    logger.info(f"Starting ffmpeg vision source={SOURCE} input={VIDEO_INPUT} @ {FPS}fps -> {RESOLUTION}")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    assert proc.stdout is not None
    buffer = bytearray()
    SOI = b"\xff\xd8"  # JPEG start
    EOI = b"\xff\xd9"  # JPEG end

    try:
        while True:
            chunk = await proc.stdout.read(4096)
            if not chunk:
                break
            buffer.extend(chunk)

            # Extract complete JPEGs from the mjpeg stream
            while True:
                start = buffer.find(SOI)
                if start == -1:
                    break
                end = buffer.find(EOI, start + 2)
                if end == -1:
                    break

                jpeg = bytes(buffer[start : end + 2])
                # remove consumed bytes (keep tail for next)
                del buffer[: end + 2]

                if len(jpeg) < 1024:  # too small, skip garbage
                    continue

                b64 = base64.b64encode(jpeg).decode("utf-8")
                payload = {
                    "type": "frame",
                    "image": b64,
                    "source": SOURCE,
                    "timestamp": asyncio.get_event_loop().time(),
                    # width/height unknown without decode; bridge/client can omit or add later
                }
                await ws.send(json.dumps(payload))
    finally:
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                proc.kill()


async def stream_vision_to_bridge():
    """Connect/reconnect loop, feed frames."""
    while True:
        try:
            logger.info(f"Connecting vision to {WS_URL} ...")
            async with websockets.connect(WS_URL) as ws:
                logger.info("Connected — vision is live.")
                await stream_frames_to_bridge(ws)
        except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            logger.warning(f"Bridge connection lost ({e}). Retrying in 3s...")
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Unexpected vision error: {e}. Retrying in 5s...")
            await asyncio.sleep(5)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    # Note: first run on mac will trigger camera / screen recording permission prompts
    logger.info(f"Vision source: {SOURCE} | target FPS ~{FPS}")
    await stream_vision_to_bridge()


if __name__ == "__main__":
    import websockets  # import here so error is clear if missing

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Vision capture stopped.")
        sys.exit(0)
