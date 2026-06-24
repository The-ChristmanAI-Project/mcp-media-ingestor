"""
Pillow-based text overlays when FFmpeg drawtext is unavailable.
Rule 15: zero cost. Rule 1: must actually render visible branding.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vega.brollbaby.pillow_overlay")

NAVY = (10, 14, 26)
CYAN = (0, 245, 255)
BLUE = (0, 132, 255)
WHITE = (240, 244, 255)
MUTED = (180, 190, 210)


def _fonts(h: int):
    from PIL import ImageFont
    try:
        return (
            ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", max(36, h // 18)),
            ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", max(24, h // 32)),
            ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", max(16, h // 52)),
        )
    except OSError:
        d = ImageFont.load_default()
        return d, d, d


def render_title_card_png(
    title: str,
    subtitle: str,
    tagline: str,
    resolution: tuple[int, int],
    output_path: str,
) -> Optional[str]:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        logger.error("[PillowOverlay] Pillow not installed")
        return None

    w, h = resolution
    img = Image.new("RGB", (w, h), color=NAVY)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, int(h * 0.08)), (w, int(h * 0.08) + 3)], fill=CYAN)
    draw.rectangle([(0, int(h * 0.88)), (w, int(h * 0.88) + 3)], fill=BLUE)
    draw.rectangle([(0, 0), (6, h)], fill=BLUE)

    title_font, sub_font, tag_font = _fonts(h)

    def centered(text: str, y: int, font, color):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((w - tw) // 2, y), text, font=font, fill=color)

    line_y = int(h * 0.32)
    centered(title[:60], line_y, title_font, WHITE)
    centered(subtitle[:80], line_y + max(48, h // 14), sub_font, CYAN)
    centered(tagline[:100], int(h * 0.78), tag_font, MUTED)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def png_to_title_card_mp4(
    png_path: str,
    output_path: str,
    duration: float = 3.0,
    fps: int = 30,
) -> Optional[str]:
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", png_path,
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t", str(duration),
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-shortest",
        output_path,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            logger.error(f"[PillowOverlay] PNG→MP4 failed: {r.stderr[-400:]}")
            return None
        return output_path if Path(output_path).exists() else None
    except Exception as e:
        logger.error(f"[PillowOverlay] PNG→MP4 error: {e}")
        return None


def render_caption_png(
    caption_text: str,
    resolution: tuple[int, int],
    output_path: str,
    max_lines: int = 3,
) -> Optional[str]:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None

    w, h = resolution
    lines = textwrap.wrap(caption_text.strip(), width=40)[:max_lines]
    if not lines:
        return None

    font_size = max(28, int(h * 0.042))
    title_font, _, _ = _fonts(h)
    try:
        from PIL import ImageFont
        cap_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", font_size)
    except OSError:
        cap_font = title_font

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    line_h = font_size + 10
    block_h = len(lines) * line_h + 24
    y0 = int(h * 0.78)
    draw.rectangle([(40, y0 - 12), (w - 40, y0 + block_h)], fill=(10, 14, 26, 170))

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=cap_font)
        tw = bbox[2] - bbox[0]
        draw.text(((w - tw) // 2, y0 + i * line_h), line, font=cap_font, fill=(*CYAN, 255))

    overlay.save(output_path, "PNG")
    return output_path


def overlay_png_on_video(
    video_path: str,
    png_path: str,
    output_path: str,
    fps: int = 30,
) -> Optional[str]:
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", png_path,
        "-filter_complex", "[1:v]format=rgba[cap];[0:v][cap]overlay=0:0",
        "-map", "0:v", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        "-r", str(fps),
        output_path,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            logger.error(f"[PillowOverlay] Overlay failed: {r.stderr[-400:]}")
            return None
        return output_path if Path(output_path).exists() else None
    except Exception as e:
        logger.error(f"[PillowOverlay] Overlay error: {e}")
        return None