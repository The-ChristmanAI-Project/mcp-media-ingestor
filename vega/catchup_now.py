"""One-shot catch-up: generate all 4 daily Vega slots right now."""
import logging
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vega.daily_engine import ALL_PLATFORMS, generate_post, _pick_topic

OUT = Path(__file__).resolve().parent.parent / "vega_output" / "video"

print(f"\n{'='*60}")
print(f"VEGA CATCH-UP — {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
print("Generating all 4 daily slots (6 platforms each)")
print(f"Output: {OUT}")
print(f"{'='*60}\n")

for slot in range(4):
    print(f"\n>>> SLOT {slot + 1}/4 starting (production / brollbaby)...")
    topic = _pick_topic()
    results = []
    for platform in ALL_PLATFORMS:
        r = generate_post(slot, platform, topic=topic, method="brollbaby", quiet=True)
        results.append(r)
    ok = sum(1 for r in results if r.get("status") == "ok")
    print(f">>> SLOT {slot + 1}/4 done — {ok}/{len(ALL_PLATFORMS)} ready | Topic: {topic}\n")

files = sorted(OUT.glob("vega_*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
print(f"\n{'='*60}")
print(f"CATCH-UP COMPLETE — {len(files)} total videos in output folder")
print("Latest files:")
for f in files[:24]:
    mb = f.stat().st_size / (1024 * 1024)
    print(f"  {f.name}  ({mb:.1f} MB)")
print(f"{'='*60}\n")