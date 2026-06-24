"""
video/assembler.py — Vega
FFmpeg-based video assembly engine.
Takes B-roll clips and assembles them into a final video.
Handles trimming, concatenation, audio overlay, scaling to target resolution.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply. Rule 13 is gospel.
"""

import logging
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vega.video.assembler")

OUTPUT_DIR = Path(__file__).parent.parent.parent / "vega_output" / "video"


def _check_ffmpeg() -> bool:
    """Verify FFmpeg is installed. Fails loud if not. (Rule 6)"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def get_video_duration(filepath: str) -> Optional[float]:
    """
    Get actual video duration using ffprobe.
    Rule 13: Returns the real duration or None — never invents a number.
    """
    if not Path(filepath).exists():
        logger.error(f"[Vega.Assembler] File not found: {filepath}")
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath,
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"[Vega.Assembler] ffprobe error: {e}")
    return None


def assemble_from_clips(
    clips: list[dict],
    output_filename: Optional[str] = None,
    target_resolution: tuple = (7680, 4320),
    target_duration_sec: Optional[int] = None,
    audio_track: Optional[str] = None,
    fps: int = 24,
) -> dict:
    """
    Assemble a list of B-roll clips into a single video.

    clips: list of dicts with 'path' key (real file paths from broll.py)
    target_resolution: (width, height) — default 8K
    target_duration_sec: trim/loop total to this length if provided
    audio_track: path to audio file to overlay
    fps: output frame rate

    Returns:
        {"status": "ok"|"error", "output_path": str, "duration": float}
    """
    if not _check_ffmpeg():
        raise RuntimeError(
            "[Vega.Assembler] FFmpeg not found. "
            "Install with: brew install ffmpeg (Rule 1: can't work without the tool)"
        )

    if not clips:
        return {"status": "error", "reason": "No clips provided to assemble."}

    # Validate all clip paths exist before doing anything
    valid_clips = []
    for clip in clips:
        path = clip.get("path", "")
        if Path(path).exists():
            valid_clips.append(path)
        else:
            logger.warning(f"[Vega.Assembler] Clip not found, skipping: {path}")

    if not valid_clips:
        return {
            "status": "error",
            "reason": "No valid clip files found. Rule 1: assembly requires real files.",
        }

    output_dir = _ensure_output_dir()
    if not output_filename:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_filename = f"vega_video_{ts}.mp4"

    output_path = str(output_dir / output_filename)
    w, h = target_resolution

    # Build FFmpeg concat file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as concat_file:
        concat_path = concat_file.name
        for clip_path in valid_clips:
            concat_file.write(f"file '{clip_path}'\n")

    try:
        # Base FFmpeg command: concat + scale to target resolution
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_path,
        ]

        # Add audio track if provided
        if audio_track and Path(audio_track).exists():
            cmd += ["-i", audio_track]

        # Video filters: scale + fps
        vf = f"scale={w}:{h}:flags=lanczos,fps={fps}"
        cmd += ["-vf", vf]

        # Audio mapping
        if audio_track and Path(audio_track).exists():
            cmd += ["-map", "0:v", "-map", "1:a", "-shortest"]
        else:
            cmd += ["-map", "0:v"]

        # Trim to target duration if specified
        if target_duration_sec:
            cmd += ["-t", str(target_duration_sec)]

        # Output encoding
        cmd += [
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", "18",
            "-c:a", "aac" if audio_track else "copy",
            output_path,
        ]

        logger.info(f"[Vega.Assembler] Running FFmpeg: {' '.join(cmd[:8])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

        if result.returncode != 0:
            logger.error(f"[Vega.Assembler] FFmpeg failed:\n{result.stderr[-2000:]}")
            return {
                "status": "error",
                "reason": f"FFmpeg assembly failed: {result.stderr[-500:]}",
            }

        # Verify output exists and get real duration
        if not Path(output_path).exists():
            return {"status": "error", "reason": "FFmpeg ran but output file not created."}

        real_duration = get_video_duration(output_path)
        file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)

        logger.info(
            f"[Vega.Assembler] Assembly complete: {output_filename} "
            f"({file_size_mb:.1f} MB, {real_duration:.1f}s)"
        )
        return {
            "status": "ok",
            "output_path": output_path,
            "output_filename": output_filename,
            "duration_sec": real_duration,
            "resolution": f"{w}x{h}",
            "fps": fps,
            "file_size_mb": round(file_size_mb, 2),
            "clips_used": len(valid_clips),
        }

    except subprocess.TimeoutExpired:
        return {"status": "error", "reason": "FFmpeg timed out after 60 minutes."}
    finally:
        os.unlink(concat_path)


def scale_video_to_8k(
    input_path: str,
    output_filename: Optional[str] = None,
    fps: int = 24,
) -> dict:
    """
    Upscale an existing video to 8K resolution using FFmpeg + lanczos.
    For true AI upscaling, Real-ESRGAN integration is needed (see generator.py).
    """
    if not _check_ffmpeg():
        raise RuntimeError("[Vega.Assembler] FFmpeg not found.")

    if not Path(input_path).exists():
        return {"status": "error", "reason": f"Input not found: {input_path}"}

    output_dir = _ensure_output_dir()
    if not output_filename:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_filename = f"vega_8k_{ts}.mp4"
    output_path = str(output_dir / output_filename)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", f"scale=7680:4320:flags=lanczos,fps={fps}",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "copy",
        output_path,
    ]

    logger.info(f"[Vega.Assembler] Scaling to 8K: {input_path}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        if result.returncode != 0:
            return {"status": "error", "reason": result.stderr[-500:]}
        return {"status": "ok", "output_path": output_path, "resolution": "7680x4320"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "reason": "8K scaling timed out."}
