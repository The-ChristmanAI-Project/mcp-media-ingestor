"""
vega/brollbaby/title_card.py — B-Roll Baby Helper 3
FFmpeg-based TCAP branded title card generator.

Builds a 3-second opening card in TCAP brand colors — navy background,
cyan headline, blue accent line — then prepends it to any video.
No external tools. No paid services. Pure FFmpeg drawtext.

Rule 15: Zero cost. FFmpeg only.
Rule 16: This is a helper. Call it before final assembly, not instead of it.
Rule 13: If FFmpeg isn't available, returns None and says so. Never fakes success.

Author: Everett Christman / The Christman AI Project
Part of: B-Roll Baby
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vega.brollbaby.title_card")

# ── TCAP Brand Colors (hex → FFmpeg color format) ────────────────────────────
NAVY   = "0x0A0E1A"
DEEP   = "0x00050F"
CYAN   = "0x00F5FF"
BLUE   = "0x0084FF"
WHITE  = "0xF0F4FF"
AMBER  = "0xFFB800"

CARD_DURATION = 3     # seconds
FADE_DURATION = 0.4   # fade in/out


def _ffmpeg_available() -> bool:
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def build_title_card(
    title:       str,
    subtitle:    str = "The Christman AI Project",
    tagline:     str = "Luma Cognify AI  ·  AI That Empowers, Protects, and Redefines Humanity",
    resolution:  tuple = (1920, 1080),
    output_path: Optional[str] = None,
    fps:         int = 30,
) -> Optional[str]:
    """
    Generate a 3-second TCAP branded title card as an MP4.

    Uses FFmpeg lavfi color source + drawtext filters.
    No image files needed. No fonts to install beyond system defaults.

    Args:
        title:       Main headline (e.g. "AlphaVox")
        subtitle:    Secondary line (default: project name)
        tagline:     Bottom tagline
        resolution:  (width, height) — match your target video
        output_path: Where to write the card. Auto-generated if None.
        fps:         Frame rate — must match target video.

    Returns:
        Path to the generated card MP4, or None on failure (Rule 13).
    """
    if not _ffmpeg_available():
        logger.error("[B-Roll Baby / TitleCard] FFmpeg not found — cannot build title card.")
        return None

    w, h = resolution
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix="_title_card.mp4", delete=False)
        output_path = tmp.name
        tmp.close()

    # ── Sanitize text for FFmpeg drawtext ────────────────────────────────────
    def _esc(text: str) -> str:
        return text.replace("'", "\\'").replace(":", "\\:").replace(",", "\\,")

    title_esc    = _esc(title[:60])
    subtitle_esc = _esc(subtitle[:80])
    tagline_esc  = _esc(tagline[:100])

    # ── Font sizes relative to resolution ────────────────────────────────────
    title_size    = max(48, h // 18)
    subtitle_size = max(28, h // 32)
    tagline_size  = max(18, h // 52)
    line_y        = int(h * 0.38)

    # ── FFmpeg filter complex ─────────────────────────────────────────────────
    # Background: deep navy gradient via two color sources blended
    # Accent line: cyan horizontal rule
    # Text layers: title (white), subtitle (cyan), tagline (gray), accent dot

    filter_complex = (
        # Background
        f"color=c={DEEP}:s={w}x{h}:d={CARD_DURATION}:r={fps}[bg];"

        # Cyan accent bar (top)
        f"[bg]drawbox="
        f"x=0:y={int(h*0.08)}:w={w}:h=3:color={CYAN}@0.8:t=fill[bg1];"

        # Cyan accent bar (bottom)
        f"[bg1]drawbox="
        f"x=0:y={int(h*0.88)}:w={w}:h=3:color={CYAN}@0.5:t=fill[bg2];"

        # Blue side accent (left edge)
        f"[bg2]drawbox="
        f"x=0:y=0:w=6:h={h}:color={BLUE}@0.7:t=fill[bg3];"

        # Title text — white, centered
        f"[bg3]drawtext="
        f"text='{title_esc}':"
        f"fontsize={title_size}:"
        f"fontcolor={WHITE}:"
        f"x=(w-text_w)/2:"
        f"y={line_y}:"
        f"alpha='if(lt(t,{FADE_DURATION}),t/{FADE_DURATION},1)'[t1];"

        # Subtitle — cyan, below title
        f"[t1]drawtext="
        f"text='{subtitle_esc}':"
        f"fontsize={subtitle_size}:"
        f"fontcolor={CYAN}:"
        f"x=(w-text_w)/2:"
        f"y={line_y + title_size + 18}:"
        f"alpha='if(lt(t,{FADE_DURATION}),t/{FADE_DURATION},1)'[t2];"

        # Divider line (drawn as thin box between subtitle and tagline)
        f"[t2]drawbox="
        f"x=(w-400)/2:y={line_y + title_size + subtitle_size + 36}:"
        f"w=400:h=1:color={CYAN}@0.4:t=fill[t3];"

        # Tagline — muted white, near bottom
        f"[t3]drawtext="
        f"text='{tagline_esc}':"
        f"fontsize={tagline_size}:"
        f"fontcolor={WHITE}@0.55:"
        f"x=(w-text_w)/2:"
        f"y={int(h * 0.78)}:"
        f"alpha='if(lt(t,{FADE_DURATION}),t/{FADE_DURATION},1)'[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000",
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "0:a",
        "-t", str(CARD_DURATION),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-r", str(fps),
        "-shortest",
        output_path,
    ]

    logger.info(f"[B-Roll Baby / TitleCard] Building card: '{title}' → {output_path}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.warning(
                "[B-Roll Baby / TitleCard] FFmpeg drawtext unavailable — Pillow fallback"
            )
            return _build_title_card_pillow(
                title, subtitle, tagline, resolution, output_path, fps
            )
        if not Path(output_path).exists():
            logger.error("[B-Roll Baby / TitleCard] FFmpeg ran but no output file.")
            return None
        logger.info(f"[B-Roll Baby / TitleCard] ✅ Card built: {output_path}")
        return output_path
    except subprocess.TimeoutExpired:
        logger.error("[B-Roll Baby / TitleCard] FFmpeg timed out building title card.")
        return None
    except Exception as e:
        logger.error(f"[B-Roll Baby / TitleCard] Unexpected error: {e}")
        return None


def _build_title_card_pillow(
    title: str,
    subtitle: str,
    tagline: str,
    resolution: tuple,
    output_path: str,
    fps: int,
) -> Optional[str]:
    from .pillow_overlay import png_to_title_card_mp4, render_title_card_png

    png_path = str(Path(output_path).with_suffix(".png"))
    if not render_title_card_png(title, subtitle, tagline, resolution, png_path):
        return None
    result = png_to_title_card_mp4(png_path, output_path, CARD_DURATION, fps)
    if result:
        logger.info(f"[B-Roll Baby / TitleCard] ✅ Pillow card built: {output_path}")
    return result


def prepend_card_to_video(
    card_path:   str,
    video_path:  str,
    output_path: str,
    fps:         int = 30,
) -> Optional[str]:
    """
    Concatenate the title card in front of a video using FFmpeg concat.
    Returns the output path on success, None on failure. (Rule 13)
    """
    if not Path(card_path).exists():
        logger.error(f"[B-Roll Baby / TitleCard] Card not found: {card_path}")
        return None
    if not Path(video_path).exists():
        logger.error(f"[B-Roll Baby / TitleCard] Video not found: {video_path}")
        return None

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as cf:
        cf.write(f"file '{card_path}'\n")
        cf.write(f"file '{video_path}'\n")
        concat_path = cf.name

    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_path,
            "-map", "0:v",
            "-map", "0:a?",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-r", str(fps),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"[B-Roll Baby / TitleCard] Concat failed:\n{result.stderr[-800:]}")
            return None
        logger.info(f"[B-Roll Baby / TitleCard] ✅ Card prepended: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"[B-Roll Baby / TitleCard] Prepend error: {e}")
        return None
    finally:
        import os
        try:
            os.unlink(concat_path)
        except Exception:
            pass
