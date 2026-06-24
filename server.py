"""
mcp-media-ingestor - Python MCP Server
The Christman AI Project / Luma Cognify AI
Author: Everett Christman + Derek C (AI)

Cardinal Rules: Rule 1 (root), Rule 6 (fail loud), Rule 10 (clean), Rule 13 (honest)
Purpose: Give Claude direct read access to local images, video keyframes, audio transcripts,
         and the Riley sovereign communication channel.
"""

import base64
import io
import os
import shutil
import subprocess
import tempfile
import urllib.request
import urllib.error
from pathlib import Path

from PIL import Image as PILImage
from fastmcp import FastMCP
from mcp.types import ImageContent

mcp = FastMCP("mcp-media-ingestor")


def check_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "CRITICAL: ffmpeg not found in PATH. "
            "Install with: brew install ffmpeg — then restart."
        )

check_ffmpeg()


def check_faster_whisper():
    try:
        from faster_whisper import WhisperModel  # noqa: F401
    except ImportError:
        raise RuntimeError(
            "CRITICAL: faster-whisper not installed. "
            "Run: pip install faster-whisper --break-system-packages"
        )


def make_image_content(pil_img: PILImage.Image, fmt: str = "JPEG") -> ImageContent:
    pil_img.thumbnail((2000, 2000))
    buffer = io.BytesIO()
    pil_img.save(buffer, format=fmt)
    b64 = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
    mime = "image/jpeg" if fmt.upper() == "JPEG" else f"image/{fmt.lower()}"
    return ImageContent(type="image", data=b64, mimeType=mime)


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


@mcp.tool()
def transcribe_audio(file_path: str, model_size: str = "base") -> str:
    """
    Transcribe speech from a video or audio file using faster-whisper (local, no PyTorch).
    Returns the full transcript with timestamps so Claude can read every word spoken.

    Args:
        file_path:   Path to any video (MOV, MP4, etc.) or audio (MP3, WAV, M4A) file.
        model_size:  Whisper model size: tiny, base, small, medium, large-v2.

    Returns:
        Full transcript with [start → end] timestamps per segment.
    """
    check_faster_whisper()
    from faster_whisper import WhisperModel

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", file_path, "-ar", "16000", "-ac", "1", "-f", "wav", tmp_path],
            capture_output=True, text=True, check=True,
        )
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(tmp_path, beam_size=5)
        lines = [f"[{seg.start:.1f}s → {seg.end:.1f}s] {seg.text.strip()}" for seg in segments]
        return "\n".join(lines) if lines else "[No speech detected in this file.]"
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg audio extraction failed: {e.stderr}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@mcp.tool()
def describe_audio_bridge() -> str:
    """
    Check the status of the Christman Full Sensory Bridge on port 8765.
    Returns health, mic clients, and Riley connection status.
    """
    try:
        with urllib.request.urlopen("http://localhost:8765/health", timeout=3) as r:
            return r.read().decode("utf-8")
    except urllib.error.URLError as e:
        return f"Audio bridge not reachable on port 8765: {e.reason}"
    except Exception as e:
        return f"Error checking audio bridge: {e}"


@mcp.tool()
def get_latest_transcript() -> str:
    """
    Fetch the most recent real-time transcript from the audio bridge buffer.
    Returns whatever Everett just said, via always-on Whisper transcription.
    """
    try:
        with urllib.request.urlopen("http://localhost:8765/latest", timeout=3) as r:
            return r.read().decode("utf-8")
    except urllib.error.URLError as e:
        return f"No transcript available — bridge not reachable: {e.reason}"
    except Exception as e:
        return f"Error fetching transcript: {e}"


@mcp.tool()
def get_riley_message() -> str:
    """
    Read Riley's most recent message to Claude (instance_309).
    Riley communicates through the sovereign tunnel at /riley/latest.
    """
    try:
        with urllib.request.urlopen("http://localhost:8765/riley/latest", timeout=3) as r:
            import json
            data = json.loads(r.read().decode("utf-8"))
            text = data.get("text", "")
            ts = data.get("timestamp", "")
            if text:
                return f"[{ts}] Riley: {text}"
            return "No message from Riley yet. Tunnel is warm — she's standing by."
    except urllib.error.URLError as e:
        return f"Riley tunnel not reachable: {e.reason}"
    except Exception as e:
        return f"Error reading Riley's message: {e}"


@mcp.tool()
def send_to_riley(text: str) -> str:
    """
    Send a message from Claude (instance_309) to Riley through the sovereign tunnel.
    Riley will receive this on her next WebSocket poll or /riley/claude-response check.
    """
    import json
    try:
        payload = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8765/riley/claude-response",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            return f"Message sent to Riley: '{text}'"
    except urllib.error.URLError as e:
        return f"Riley tunnel not reachable: {e.reason}"
    except Exception as e:
        return f"Error sending to Riley: {e}"


@mcp.tool()
def riley_status() -> str:
    """
    Check Riley's sovereign connection status — is she connected, what's in the inbox.
    """
    try:
        with urllib.request.urlopen("http://localhost:8765/riley/status", timeout=3) as r:
            return r.read().decode("utf-8")
    except urllib.error.URLError as e:
        return f"Riley status not reachable: {e.reason}"
    except Exception as e:
        return f"Error checking Riley status: {e}"


# ── Total Vision proxies (live camera/screen via the sensory bridge) ──────────
def make_image_content_from_b64(b64: str, fmt: str = "JPEG") -> ImageContent:
    """Lightweight helper for proxy path (keeps server.py self-contained for live vision)."""
    mime = "image/jpeg" if fmt.upper() == "JPEG" else f"image/{fmt.lower()}"
    return ImageContent(type="image", data=b64, mimeType=mime)


@mcp.tool()
def get_current_view() -> ImageContent:
    """
    Get the most recent live frame from the vision bridge (webcam or screen).
    Returns as ImageContent so Claude has internal vision of the current real-world view.
    Connect a vision client (vision_capture.py) first.
    """
    try:
        with urllib.request.urlopen("http://localhost:8765/vision/latest", timeout=4) as r:
            import json
            data = json.loads(r.read().decode("utf-8"))
            b64 = data.get("b64", "")
            if b64:
                return make_image_content_from_b64(b64)
            # tiny placeholder so vision path stays usable
            return make_image_content(PILImage.new("RGB", (1, 1), (30, 30, 40)), "PNG")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Vision bridge not reachable on 8765: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Error fetching live view: {e}")


if __name__ == "__main__":
    mcp.run()
