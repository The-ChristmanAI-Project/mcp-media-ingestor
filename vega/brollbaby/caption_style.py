"""
vega/brollbaby/caption_style.py — B-Roll Baby Helper 5
TCAP branded caption overlay for Vega videos.

Burns captions in TCAP cyan — bold, bottom third, brand-consistent.
Replaces the plain unstyled captions from the old pipeline.
FFmpeg only. Zero cost. Zero compromise.

Rule 15: No paid captioning services. FFmpeg drawtext handles this.
Rule 13: If no caption text is provided, returns the original video unchanged.
Rule 16: This is a helper. It runs after assembly, not instead of it.

Author: Everett Christman / The Christman AI Project
Part of: B-Roll Baby
"""

import logging
import subprocess
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


def burn_captions(
    video_path:   str,
    caption_text: str,
    output_path:  str,
    resolution:   tuple = (1920, 1080),
    fps:          int = 30,
) -> Optional[str]:
    """
    Burn styled TCAP captions onto a video using FFmpeg drawtext.

    Splits caption_text into lines, centers them, applies TCAP cyan
    with a dark navy backing box for readability.

    Args:
        video_path:   Input video file.
        caption_text: Full text to display as caption (auto-wrapped).
        output_path:  Where to write the captioned video.
        resolution:   (width, height) of the video.
        fps:          Frame rate.

    Returns:
        output_path on success, None on failure (Rule 13).
    """
    if not caption_text or not caption_text.strip():
        logger.info("[B-Roll Baby / Captions] No caption text — returning video unchanged.")
        return video_path

    if not Path(video_path).exists():
        logger.error(f"[B-Roll Baby / Captions] Video not found: {video_path}")
        return None

    w, h = resolution
    font_size = max(28, int(h * FONT_SIZE_RATIO))
    y_pos     = int(h * BOTTOM_MARGIN)

    # ── Wrap text to fit the frame ────────────────────────────────────────────
    lines = textwrap.wrap(caption_text.strip(), width=MAX_LINE_WIDTH)
    if not lines:
        return video_path

    # ── Build drawtext filters, one per line ──────────────────────────────────
    def _esc(s: str) -> str:
        return s.replace("'", "\\'").replace(":", "\\:").replace(",", "\\,").replace("[", "\\[").replace("]", "\\]")

    filters = []
    line_height = font_size + 8

    for i, line in enumerate(lines[:4]):   # max 4 lines visible at once
        y = y_pos + (i * line_height)
        filters.append(
            f"drawtext="
            f"text='{_esc(line)}':"
            f"fontsize={font_size}:"
            f"fontcolor={CAPTION_COLOR}:"
            f"shadowcolor={SHADOW_COLOR}:"
            f"shadowx=2:shadowy=2:"
            f"box=1:boxcolor={BOX_COLOR}:boxborderw=8:"
            f"x=(w-text_w)/2:"
            f"y={y}"
        )

    vf = ",".join(filters)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", vf,
        "-map", "0:v",
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        "-r", str(fps),
        output_path,
    ]

    logger.info(f"[B-Roll Baby / Captions] Burning {len(lines)} caption lines → {output_path}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.warning("[B-Roll Baby / Captions] drawtext unavailable — Pillow fallback")
            return _burn_captions_pillow(
                video_path, caption_text, output_path, resolution, fps
            )
        if not Path(output_path).exists():
            logger.error("[B-Roll Baby / Captions] FFmpeg ran but no output file.")
            return None
        logger.info(f"[B-Roll Baby / Captions] ✅ Captions burned: {output_path}")
        return output_path
    except subprocess.TimeoutExpired:
        logger.error("[B-Roll Baby / Captions] Timed out burning captions.")
        return None
    except Exception as e:
        logger.error(f"[B-Roll Baby / Captions] Error: {e}")
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
