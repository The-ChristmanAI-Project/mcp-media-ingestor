"""
vega/brollbaby/caption_style.py — B-Roll Baby Helper 5
TCAP branded caption overlay for Vega videos.

Burns captions in TCAP cyan — bold, bottom third, brand-consistent.
Replaces the plain unstyled captions from the old pipeline.
FFmpeg only. Zero cost. Zero compromise.

Strategy order:
  1. ASS subtitles via libass (works on Mac ffmpeg without libfreetype)
  2. drawtext via libfreetype (Linux/Homebrew ffmpeg with full build)
  3. Pillow PNG overlay (universal fallback)

Rule 15: No paid captioning services. FFmpeg handles this.
Rule 13: If no caption text is provided, returns the original video unchanged.
Rule 16: This is a helper. It runs after assembly, not instead of it.

Author: Everett Christman / The Christman AI Project
Part of: B-Roll Baby
"""

import logging
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vega.brollbaby.caption_style")

# ── TCAP Brand Caption Style ──────────────────────────────────────────────────
CAPTION_COLOR    = "0x00F5FF"     # TCAP cyan
SHADOW_COLOR     = "0x000000@0.7"
BOX_COLOR        = "0x0A0E1A@0.6"  # dark navy box behind text
FONT_SIZE_RATIO  = 0.042           # font size as fraction of video height
MAX_LINE_WIDTH   = 44              # characters per caption line
BOTTOM_MARGIN    = 0.82            # y position as fraction of height (bottom third)

# ASS color format: &HAABBGGRR (alpha, blue, green, red)
ASS_CYAN    = "&H00FFF500"   # TCAP cyan in ASS BGR order
ASS_NAVY_BG = "&HAA1A0E0A"  # dark navy, ~67% opaque


def burn_captions(
    video_path:   str,
    caption_text: str,
    output_path:  str,
    resolution:   tuple = (1920, 1080),
    fps:          int = 30,
) -> Optional[str]:
    """
    Burn styled TCAP captions onto a video.

    Tries three strategies in order:
      1. ASS subtitle file + libass (no libfreetype needed — works on stock Mac ffmpeg)
      2. drawtext filter (needs libfreetype — works on full Linux/Homebrew build)
      3. Pillow PNG overlay (universal fallback)

    Returns output_path on success, None on failure (Rule 13).
    """
    if not caption_text or not caption_text.strip():
        logger.info("[B-Roll Baby / Captions] No caption text — returning video unchanged.")
        return video_path

    if not Path(video_path).exists():
        logger.error(f"[B-Roll Baby / Captions] Video not found: {video_path}")
        return None

    lines = textwrap.wrap(caption_text.strip(), width=MAX_LINE_WIDTH)
    if not lines:
        return video_path

    # Strategy 1: ASS subtitles (libass — available on Mac stock ffmpeg)
    result = _burn_captions_ass(video_path, lines, output_path, resolution, fps)
    if result and Path(result).exists():
        logger.info(f"[B-Roll Baby / Captions] ✅ ASS captions burned: {output_path}")
        return result

    # Strategy 2: drawtext (libfreetype — Linux / full Homebrew ffmpeg)
    result = _burn_captions_drawtext(video_path, lines, output_path, resolution, fps)
    if result and Path(result).exists():
        logger.info(f"[B-Roll Baby / Captions] ✅ drawtext captions burned: {output_path}")
        return result

    # Strategy 3: Pillow PNG overlay
    logger.warning("[B-Roll Baby / Captions] FFmpeg caption methods failed — Pillow fallback")
    return _burn_captions_pillow(video_path, caption_text, output_path, resolution, fps)


# ── Strategy 1: ASS subtitles ────────────────────────────────────────────────

def _build_ass(lines: list[str], resolution: tuple, duration_sec: float = 30.0) -> str:
    """Generate an ASS subtitle file string with TCAP brand styling."""
    w, h = resolution
    font_size = max(28, int(h * FONT_SIZE_RATIO))
    margin_v  = int(h * (1.0 - BOTTOM_MARGIN))

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {w}\n"
        f"PlayResY: {h}\n"
        "WrapStyle: 0\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: TCAPCaption,Arial,{font_size},{ASS_CYAN},&H000000FF,"
        f"&H00000000,{ASS_NAVY_BG},1,0,0,0,100,100,0,0,3,2,1,"
        f"2,10,10,{margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    # Show all lines as one event for the full clip duration
    text = r"\N".join(lines[:4])
    end_ts = _ass_ts(duration_sec)
    event = f"Dialogue: 0,0:00:00.00,{end_ts},TCAPCaption,,0,0,0,,{text}\n"

    return header + event


def _ass_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _burn_captions_ass(
    video_path: str,
    lines: list[str],
    output_path: str,
    resolution: tuple,
    fps: int,
) -> Optional[str]:
    """Burn captions using an ASS subtitle file and libass."""
    try:
        # Probe video duration so the caption covers the full clip
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=15,
        )
        duration = float(probe.stdout.strip()) if probe.returncode == 0 else 30.0
    except Exception:
        duration = 30.0

    ass_content = _build_ass(lines, resolution, duration_sec=duration)

    with tempfile.NamedTemporaryFile(
        suffix=".ass", delete=False, mode="w", encoding="utf-8"
    ) as tmp:
        tmp.write(ass_content)
        ass_path = tmp.name

    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"ass={ass_path}",
            "-map", "0:v",
            "-map", "0:a?",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "copy",
            "-r", str(fps),
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.debug(f"[B-Roll Baby / Captions] ASS failed: {result.stderr[-300:]}")
            return None
        return output_path if Path(output_path).exists() else None
    except subprocess.TimeoutExpired:
        logger.error("[B-Roll Baby / Captions] ASS burn timed out.")
        return None
    except Exception as e:
        logger.debug(f"[B-Roll Baby / Captions] ASS error: {e}")
        return None
    finally:
        try:
            Path(ass_path).unlink(missing_ok=True)
        except Exception:
            pass


# ── Strategy 2: drawtext ─────────────────────────────────────────────────────

def _burn_captions_drawtext(
    video_path: str,
    lines: list[str],
    output_path: str,
    resolution: tuple,
    fps: int,
) -> Optional[str]:
    """Burn captions using FFmpeg drawtext (requires libfreetype)."""
    w, h = resolution
    font_size  = max(28, int(h * FONT_SIZE_RATIO))
    y_pos      = int(h * BOTTOM_MARGIN)
    line_height = font_size + 8

    def _esc(s: str) -> str:
        return (s.replace("\\", "\\\\")
                 .replace("'", "\\'")
                 .replace(":", "\\:")
                 .replace(",", "\\,")
                 .replace("[", "\\[")
                 .replace("]", "\\]"))

    filters = []
    for i, line in enumerate(lines[:4]):
        y = y_pos + (i * line_height)
        filters.append(
            f"drawtext=text='{_esc(line)}':"
            f"fontsize={font_size}:"
            f"fontcolor={CAPTION_COLOR}:"
            f"shadowcolor={SHADOW_COLOR}:"
            f"shadowx=2:shadowy=2:"
            f"box=1:boxcolor={BOX_COLOR}:boxborderw=8:"
            f"x=(w-text_w)/2:y={y}"
        )

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", ",".join(filters),
        "-map", "0:v", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        "-r", str(fps),
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.debug(f"[B-Roll Baby / Captions] drawtext failed: {result.stderr[-300:]}")
            return None
        return output_path if Path(output_path).exists() else None
    except subprocess.TimeoutExpired:
        logger.error("[B-Roll Baby / Captions] drawtext burn timed out.")
        return None
    except Exception as e:
        logger.debug(f"[B-Roll Baby / Captions] drawtext error: {e}")
        return None


def _burn_captions_pillow(
    video_path: str,
    caption_text: str,
    output_path: str,
    resolution: tuple,
    fps: int,
) -> Optional[str]:
    import tempfile
    from .pillow_overlay import overlay_png_on_video, render_caption_png

    with tempfile.NamedTemporaryFile(suffix="_caption.png", delete=False) as tmp:
        png_path = tmp.name
    if not render_caption_png(caption_text, resolution, png_path):
        return None
    result = overlay_png_on_video(video_path, png_path, output_path, fps)
    if result:
        logger.info(f"[B-Roll Baby / Captions] ✅ Pillow captions: {output_path}")
    try:
        Path(png_path).unlink(missing_ok=True)
    except Exception:
        pass
    return result
