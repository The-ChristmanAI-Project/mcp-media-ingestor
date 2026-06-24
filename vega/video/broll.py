"""
video/broll.py — Vega
B-roll footage scanner and indexer for /Volumes/LIFE2.
Finds, categorizes, and retrieves existing footage for video assembly.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply. Rule 13 is gospel.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vega.video.broll")

FOOTAGE_LIBRARY = Path("/Volumes/LIFE2")
INDEX_FILE = Path(__file__).parent.parent / "data" / "broll_index.json"

# Supported video extensions
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".mxf", ".prores", ".hevc"}

# Supported image extensions (for still cutaways)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".raw", ".arw", ".cr2"}


def scan_library(
    base_path: Optional[str] = None,
    rebuild_index: bool = False,
) -> dict:
    """
    Scan /Volumes/LIFE2 (or provided path) for all video and image assets.
    Builds an index of available footage for the assembler.

    Rule 13: Only indexes files that actually exist. Never fabricates entries.
    Rule 1: This must actually work — it reads real files.

    Returns:
        {
            "total_videos": int,
            "total_images": int,
            "total_size_gb": float,
            "categories": dict,
            "index_path": str,
        }
    """
    library = Path(base_path) if base_path else FOOTAGE_LIBRARY

    if not library.exists():
        logger.warning(f"[Vega.BRoll] Footage library not mounted: {library}")
        return {
            "status": "error",
            "reason": f"Footage library not found at {library}. "
                      "Is LIFE2 mounted? (Rule 1: can't work with what isn't there)",
            "total_videos": 0,
            "total_images": 0,
        }

    if INDEX_FILE.exists() and not rebuild_index:
        logger.info("[Vega.BRoll] Loading existing index")
        with open(INDEX_FILE) as f:
            return json.load(f)

    logger.info(f"[Vega.BRoll] Scanning footage library: {library}")
    videos = []
    images = []
    total_bytes = 0

    for root, dirs, files in os.walk(library):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for filename in files:
            if filename.startswith("."):
                continue

            filepath = Path(root) / filename
            suffix = filepath.suffix.lower()

            try:
                size = filepath.stat().st_size
                total_bytes += size
            except OSError:
                continue

            relative = str(filepath.relative_to(library))

            if suffix in VIDEO_EXTENSIONS:
                videos.append({
                    "path": str(filepath),
                    "relative": relative,
                    "name": filename,
                    "size_mb": round(size / (1024 * 1024), 2),
                    "extension": suffix,
                    "folder": Path(root).name,
                })
            elif suffix in IMAGE_EXTENSIONS:
                images.append({
                    "path": str(filepath),
                    "relative": relative,
                    "name": filename,
                    "size_mb": round(size / (1024 * 1024), 2),
                    "extension": suffix,
                    "folder": Path(root).name,
                })

    # Categorize by folder name
    categories: dict[str, list] = {}
    for clip in videos:
        folder = clip["folder"]
        categories.setdefault(folder, []).append(clip["relative"])

    index = {
        "status": "ok",
        "scanned_at": datetime.utcnow().isoformat(),
        "library_path": str(library),
        "total_videos": len(videos),
        "total_images": len(images),
        "total_size_gb": round(total_bytes / (1024 ** 3), 2),
        "categories": categories,
        "videos": videos,
        "images": images,
    }

    # Save index
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)

    logger.info(
        f"[Vega.BRoll] Scan complete: {len(videos)} videos, "
        f"{len(images)} images, {index['total_size_gb']} GB"
    )
    return index


def find_clips(
    keywords: list[str],
    max_clips: int = 10,
    extensions: Optional[set] = None,
) -> list[dict]:
    """
    Find clips matching keywords in filename or folder path.
    Used by the assembler to pick relevant B-roll for a given prompt.

    Returns list of matching clip dicts (with real file paths).
    Rule 13: Only returns files that actually exist.
    """
    if not INDEX_FILE.exists():
        logger.info("[Vega.BRoll] No index found — running scan first")
        scan_library()

    if not INDEX_FILE.exists():
        return []

    with open(INDEX_FILE) as f:
        index = json.load(f)

    allowed_ext = extensions or VIDEO_EXTENSIONS
    clips = [v for v in index.get("videos", []) if v["extension"] in allowed_ext]

    if not keywords:
        # No keywords — return up to max_clips random selections
        return clips[:max_clips]

    matches = []
    for clip in clips:
        search_text = (clip["name"] + " " + clip["relative"]).lower()
        if any(kw.lower() in search_text for kw in keywords):
            matches.append(clip)
        if len(matches) >= max_clips:
            break

    # Fallback: if nothing matched keywords, return any available clips
    if not matches:
        logger.warning(
            f"[Vega.BRoll] No keyword matches for {keywords} — using first available clips"
        )
        matches = clips[:max_clips]

    return matches


def get_index_summary() -> dict:
    """
    Return a quick summary of the B-roll index without doing a full rescan.
    Returns empty summary if no index exists yet.
    """
    if not INDEX_FILE.exists():
        return {
            "indexed": False,
            "total_videos": 0,
            "total_images": 0,
            "categories": [],
        }

    with open(INDEX_FILE) as f:
        index = json.load(f)

    return {
        "indexed": True,
        "scanned_at": index.get("scanned_at"),
        "library_path": index.get("library_path"),
        "total_videos": index.get("total_videos", 0),
        "total_images": index.get("total_images", 0),
        "total_size_gb": index.get("total_size_gb", 0),
        "categories": list(index.get("categories", {}).keys()),
    }
