"""
_paths.py — Christman Family Path Bootstrap
Ensures all Christman AI family modules are importable.
"""
import sys
import os

FAMILY_ROOTS = [
    "/Users/EverettN/Claude-Cowork/mcp-media-ingestor",
    "/Users/EverettN/Claude-Cowork",
    "/Volumes/LIFE",
]

def ensure_family_paths():
    for root in FAMILY_ROOTS:
        if os.path.isdir(root) and root not in sys.path:
            sys.path.insert(0, root)
