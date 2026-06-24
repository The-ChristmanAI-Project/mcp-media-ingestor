"""
vega/video/generator.py — Vega
Prompt → video generation pipeline.

B-Roll Baby is in charge now.
Strategy 1: B-roll assembly from /Volumes/LIFE2 — real footage, real world,
            TCAP keyword brain, branded title card, styled captions.
Strategy 2: ChristmanVideoEngine — FFmpeg + GPU fallback (when LIFE2 unavailable).
Strategy 3: Honest error — no silent failures. (Rule 6, Rule 13)

We're famous now. We get it right. We get it tight.

Rule 15: RunwayML, Replicate, and all paid APIs are gone. They stay gone.
Rule 16: B-Roll Baby is the helper collective. Queue + watchdog live in queue.py.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 16 apply. Rule 13 is gospel. Rule 15 is law. Rule 16 is the standard.
"""

import logging
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── B-Roll Baby helpers ───────────────────────────────────────────────────────
from ..brollbaby.keyword_brain  import extract_keywords
from ..brollbaby.title_card     import build_title_card, prepend_card_to_video
from ..brollbaby.caption_style  import burn_captions
from .broll     import find_clips, scan_library
from .assembler import assemble_from_clips

logger = logging.getLogger("vega.video.generator")

OUTPUT_DIR = Path(__file__).parent.parent.parent / "vega_output" / "video"
TEMP_DIR   = Path(__file__).parent.parent.parent / "vega_output" / "temp"

# ChristmanVideoEngine — fallback only (Strategy 2)
CVE_PATH = Path("/Users/EverettN/ChristmanVideoEngine")

# Platform → resolution map
PLATFORM_RESOLUTION: dict[str, tuple] = {
    "youtube":    (1920, 1080),
    "linkedin":   (1920, 1080),
    "facebook":   (1920, 1080),
    "instagram":  (1080, 1080),
    "tiktok":     (1080, 1920),
    "twitter":    (1280, 720),
    "x":          (1280, 720),
}


@contextmanager
def _cve_working_dir():
    """
    Temporarily chdir into ChristmanVideoEngine so FFmpeg can find
    relative asset paths inside CVE. Restores cwd on exit.
    Rule 13: This is the real fix. The import worked. The cwd was wrong.
    """
    original = os.getcwd()
    os.chdir(str(CVE_PATH))
    try:
        yield
    finally:
        os.chdir(original)


def _get_cve():
    """
    Import ChristmanVideoEngine's quick_render.
    Rule 13: Returns None honestly if CVE isn't available.
    Rule 15: CVE is in-house. Zero cost. This is the right call.
    """
    if CVE_PATH not in [Path(p) for p in sys.path]:
        sys.path.insert(0, str(CVE_PATH))
    try:
        from modules.generator import quick_render
        return quick_render
    except ImportError as e:
        logger.warning(f"[Vega.VideoGen] ChristmanVideoEngine not available: {e}")
        return None


def _platform_resolution(platform: str) -> tuple:
    return PLATFORM_RESOLUTION.get(platform.lower(), (1920, 1080))


def _being_from_prompt(prompt: str) -> str:
    """Extract the primary being name from the prompt for the title card."""
    prompt_lower = prompt.lower()
    beings = [
        "AlphaVox", "AlphaWolf", "AlphaDen", "OmegaAlpha",
        "Omega", "Inferno", "Aegis", "Derek", "Brockston",
    ]
    for b in beings:
        if b.lower() in prompt_lower:
            return b
    return "The Christman AI Project"


def generate_from_prompt(
    prompt:            str,
    platform:          str = "youtube",
    duration_sec:      int = 30,
    use_broll:         bool = True,
    target_resolution: Optional[tuple] = None,
    output_filename:   Optional[str] = None,
) -> dict:
    """
    Main entry point: text prompt → finished, branded video.

    B-Roll Baby pipeline:
      1. Keyword Brain maps prompt to LIFE2 footage tags
      2. B-roll assembler pulls matching clips from /Volumes/LIFE2
      3. Title Card Builder prepends a 3s TCAP branded card
      4. Caption Styler burns TCAP cyan captions onto the final video

    Strategy 1: B-roll assembly (primary — real footage, real world)
    Strategy 2: ChristmanVideoEngine (fallback — when LIFE2 unavailable)
    Strategy 3: Honest error (Rule 6 — fail loud, never silent)

    Returns:
        {"status": "ok"|"error", "output_path": str, "method": str, ...}
    """
    logger.info(
        f"[Vega.VideoGen] Prompt: '{prompt[:80]}' | "
        f"Platform: {platform} | Duration: {duration_sec}s"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    if not output_filename:
        output_filename = f"vega_{platform}_{ts}.mp4"

    resolution = target_resolution or _platform_resolution(platform)
    output_path = str(OUTPUT_DIR / output_filename)

    # ══════════════════════════════════════════════════════════════════════════
    # STRATEGY 1 — B-Roll Assembly (B-Roll Baby primary pipeline)
    # ══════════════════════════════════════════════════════════════════════════
    if use_broll:
        logger.info("[Vega.VideoGen] Strategy 1: B-Roll Baby pipeline")

        # Helper 2: Keyword Brain — TCAP-aware tag extraction
        keywords = extract_keywords(prompt)
        logger.info(f"[Vega.VideoGen] Keywords: {keywords}")

        clips = find_clips(keywords, max_clips=20)

        if clips:
            # Intermediate filenames — assembler writes to OUTPUT_DIR/video
            raw_filename  = f"vega_raw_{ts}.mp4"
            card_path_out = str(TEMP_DIR / f"vega_card_{ts}.mp4")

            assembly = assemble_from_clips(
                clips=clips,
                output_filename=raw_filename,
                target_resolution=resolution,
                target_duration_sec=duration_sec,
            )

            # assembler.py writes to its own OUTPUT_DIR (vega_output/video)
            assembled = assembly.get("output_path", str(OUTPUT_DIR / raw_filename))

            if assembly.get("status") == "ok" and Path(assembled).exists():

                # Helper 3: Title Card — TCAP branded 3s opener
                being     = _being_from_prompt(prompt)
                card_file = build_title_card(
                    title=being,
                    resolution=resolution,
                    output_path=str(TEMP_DIR / f"titlecard_{ts}.mp4"),
                    fps=24,
                )

                with_card = assembled
                if card_file and Path(card_file).exists():
                    merged = prepend_card_to_video(
                        card_path=card_file,
                        video_path=assembled,
                        output_path=card_path_out,
                        fps=24,
                    )
                    if merged and Path(merged).exists():
                        with_card = merged
                        logger.info("[Vega.VideoGen] ✅ Title card prepended")
                    else:
                        logger.warning("[Vega.VideoGen] Title card prepend failed — using raw assembly")

                # Helper 5: Caption Styler — TCAP cyan branded captions
                caption_text = prompt[:180]
                final = burn_captions(
                    video_path=with_card,
                    caption_text=caption_text,
                    output_path=output_path,
                    resolution=resolution,
                    fps=24,
                )
                if final and Path(final).exists():
                    logger.info("[Vega.VideoGen] ✅ Captions burned")
                else:
                    # Captions failed — use the version without them
                    import shutil
                    shutil.copy2(with_card, output_path)
                    logger.warning("[Vega.VideoGen] Caption burn failed — using uncaptioned version")

                # Verify final output
                if Path(output_path).exists():
                    file_size = Path(output_path).stat().st_size
                    logger.info(
                        f"[Vega.VideoGen] ✅ B-Roll Baby complete: {output_filename} "
                        f"({file_size / (1024*1024):.1f} MB)"
                    )
                    return {
                        "status":       "ok",
                        "output_path":  output_path,
                        "file_size_mb": round(file_size / (1024 * 1024), 2),
                        "duration_sec": duration_sec,
                        "resolution":   f"{resolution[0]}x{resolution[1]}",
                        "method":       "broll_baby",
                        "clips_used":   assembly.get("clips_used", len(clips)),
                        "keywords":     keywords[:5],
                        "prompt":       prompt,
                    }

            logger.warning("[Vega.VideoGen] B-roll assembly failed — falling back to CVE")

    # ══════════════════════════════════════════════════════════════════════════
    # STRATEGY 2 — ChristmanVideoEngine (fallback)
    # ══════════════════════════════════════════════════════════════════════════
    quick_render = _get_cve()
    if quick_render:
        logger.info("[Vega.VideoGen] Strategy 2: ChristmanVideoEngine fallback")
        try:
            with _cve_working_dir():
                result = quick_render(prompt=prompt, output_path=output_path)
            if result.success:
                return {
                    "status":       "ok",
                    "output_path":  result.output_path,
                    "file_size_mb": round(getattr(result, "file_size", 0) / (1024 * 1024), 2),
                    "duration_sec": getattr(result, "duration", duration_sec),
                    "method":       "christman_video_engine",
                    "prompt":       prompt,
                }
            else:
                logger.warning(f"[Vega.VideoGen] CVE failed: {result.error}")
        except Exception as e:
            logger.warning(f"[Vega.VideoGen] CVE error: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # STRATEGY 3 — Honest failure (Rule 6: fail loud)
    # ══════════════════════════════════════════════════════════════════════════
    return {
        "status": "error",
        "reason": (
            "No video generation method succeeded. "
            "B-Roll Baby needs /Volumes/LIFE2 mounted with indexed footage. "
            "ChristmanVideoEngine needs its asset files present. "
            "Rule 1: it has to actually work."
        ),
        "method": "none",
        "prompt": prompt,
    }
