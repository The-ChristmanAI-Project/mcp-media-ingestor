"""
mcp-media-ingestor - Python MCP Server
The Christman AI Project / Luma Cognify AI
Author: Everett Christman + Derek C (AI)

Cardinal Rules: Rule 1 (root), Rule 6 (fail loud), Rule 10 (clean), Rule 13 (honest)
Purpose: Give Claude direct read access to local images, video keyframes, and audio transcripts.
         Internal context only — never renders media back to the user.
"""

import base64
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image as PILImage
from fastmcp import FastMCP
from mcp.types import ImageContent

# ── Named Server ──────────────────────────────────────────────────────────────
mcp = FastMCP("mcp-media-ingestor")


# ── Dependency Guards ─────────────────────────────────────────────────────────
def check_ffmpeg():
    """Rule 6: Crash loud at startup if ffmpeg is missing."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "CRITICAL: ffmpeg not found in PATH. "
            "Install with: brew install ffmpeg — then restart."
        )

check_ffmpeg()


def check_faster_whisper():
    """Rule 6: Raise clearly if faster-whisper is not installed."""
    try:
        from faster_whisper import WhisperModel  # noqa: F401
    except ImportError:
        raise RuntimeError(
            "CRITICAL: faster-whisper not installed. "
            "Run: pip install faster-whisper --break-system-packages"
        )


def make_image_content(pil_img: PILImage.Image, fmt: str = "JPEG") -> ImageContent:
    """Convert a PIL image to an MCP ImageContent block."""
    pil_img.thumbnail((2000, 2000))
    buffer = io.BytesIO()
    pil_img.save(buffer, format=fmt)
    b64 = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
    mime = "image/jpeg" if fmt.upper() == "JPEG" else f"image/{fmt.lower()}"
    return ImageContent(type="image", data=b64, mimeType=mime)


# ── Tool: read_image ──────────────────────────────────────────────────────────
@mcp.tool()
def read_image(file_path: str) -> ImageContent:
    """
    Read a local JPEG or PNG and return it as an ImageContent block for
    Claude's vision. Internal use only — not rendered to the user.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Image not found: {file_path}")
    try:
        with PILImage.open(file_path) as img:
            fmt = img.format if img.format else "JPEG"
            return make_image_content(img, fmt)
    except Exception as e:
        raise RuntimeError(f"Ingestion failed: {e}")


# ── Tool: get_video_metadata ──────────────────────────────────────────────────
@mcp.tool()
def get_video_metadata(video_path: str) -> str:
    """
    Run ffprobe to get video duration and resolution.
    Claude uses this to calculate an optimal frame sampling interval.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=width,height",
            "-of", "default=noprint_wrappers=1",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe failed: {e.stderr}")


# ── Tool: extract_video_frames ────────────────────────────────────────────────
@mcp.tool()
def extract_video_frames(video_path: str, interval_seconds: float = 5.0) -> list[ImageContent]:
    """
    Extract keyframes from a local video at a set interval.
    Returns a chronological list of ImageContent blocks for Claude to analyze.

    Sampling guidance:
      Short  (<1 min)    → interval_seconds=2
      Medium (1-10 min)  → interval_seconds=5 to 10
      Long   (>10 min)   → interval_seconds=30
    Hard cap: ~120 frames max to protect context window.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    check_ffmpeg()
    temp_dir = tempfile.mkdtemp()
    output_pattern = os.path.join(temp_dir, "frame_%04d.jpg")

    try:
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"fps=1/{interval_seconds}",
            "-vsync", "vfr",
            output_pattern,
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=True)

        frames = []
        for frame_file in sorted(Path(temp_dir).glob("frame_*.jpg")):
            with PILImage.open(frame_file) as img:
                frames.append(make_image_content(img, "JPEG"))
            os.remove(frame_file)
        return frames

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg failed: {e.stderr}")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


# ── Tool: transcribe_audio ────────────────────────────────────────────────────
@mcp.tool()
def transcribe_audio(file_path: str, model_size: str = "base") -> str:
    """
    Transcribe speech from a video or audio file using faster-whisper (local, no PyTorch).
    Returns the full transcript with timestamps so Claude can read every word spoken.

    Args:
        file_path:   Path to any video (MOV, MP4, etc.) or audio (MP3, WAV, M4A) file.
        model_size:  Whisper model size: tiny, base, small, medium, large-v2.
                     'base' is default — fast and accurate for clear English speech.
                     Use 'small' or 'medium' for accents, music, or background noise.

    Returns:
        Full transcript with [start → end] timestamps per segment.
    """
    check_faster_whisper()
    from faster_whisper import WhisperModel

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Extract audio to 16kHz mono WAV — Whisper's optimal input
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", file_path,
                "-ar", "16000",
                "-ac", "1",
                "-f", "wav",
                tmp_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # cpu + int8: runs on any machine, no GPU required
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(tmp_path, beam_size=5)

        lines = []
        for seg in segments:
            lines.append(f"[{seg.start:.1f}s → {seg.end:.1f}s] {seg.text.strip()}")

        if not lines:
            return "[No speech detected in this file.]"

        return "\n".join(lines)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg audio extraction failed: {e.stderr}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)  # Rule 10: clean up temp audio


# ── Tool: describe_audio_bridge ───────────────────────────────────────────────
@mcp.tool()
def describe_audio_bridge() -> str:
    """
    Check the status of the real-time audio bridge (realtime_audio.py on port 8765).
    Returns the bridge's health, mode, and whether always-on listening is active.
    """
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen("http://localhost:8765/health", timeout=3) as r:
            return r.read().decode("utf-8")
    except urllib.error.URLError as e:
        return f"Audio bridge not reachable on port 8765: {e.reason}"
    except Exception as e:
        return f"Error checking audio bridge: {e}"


# ── Tool: get_latest_transcript ───────────────────────────────────────────────
@mcp.tool()
def get_latest_transcript() -> str:
    """
    Fetch the most recent real-time transcript from the audio bridge buffer.
    Returns whatever Everett just said, with timestamps, via always-on Whisper transcription.
    """
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen("http://localhost:8765/latest", timeout=3) as r:
            return r.read().decode("utf-8")
    except urllib.error.URLError as e:
        return f"No transcript available — bridge not reachable: {e.reason}"
    except Exception as e:
        return f"Error fetching transcript: {e}"


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
