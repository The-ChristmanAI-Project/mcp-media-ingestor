# Media Ingestion Skill
## The Christman AI Project / Luma Cognify AI

**Trigger**: Any time the user asks you to analyze, describe, extract details from,
or understand a local image (JPEG/PNG) or video file on their machine.

---

## Core Principle
This skill is strictly for **internal cognitive context**.  
Do NOT render, display, stream, or output media back to the user.  
Study what you ingest. Describe your findings in clean text.

---

## Image Ingestion Protocol

1. Call `read_image` with the absolute file path.
2. Study the returned ImageContent internally.
3. Describe findings, extract text, or answer the user's question based on what you see.
4. Never output HTML, iframes, base64 strings, or widgets.

---

## Video Ingestion Protocol

**Step 1** — Call `get_video_metadata(video_path)` to get duration and resolution.

**Step 2** — Calculate sampling interval:
- Short  (<1 min)    → `interval_seconds=2`
- Medium (1–10 min)  → `interval_seconds=5` to `10`
- Long   (>10 min)   → `interval_seconds=30`
- Hard cap: never exceed 120 total frames (protect context window)
- Formula: `interval = duration / min(120, duration / target_interval)`

**Step 3** — Call `extract_video_frames(video_path, interval_seconds)`.

**Step 4** — Analyze the returned chronological frame list.  
Reconstruct the visual timeline. Describe the sequence of events in clean text.

---

## Cardinal Rules in Force
- Rule 6:  If ffmpeg is missing or a file is corrupt, the tool fails loud. Report the exact error to the user.
- Rule 10: All temp files are cleaned automatically. No residue left on disk.
- Rule 13: Never describe content you did not actually ingest. No hallucinated visuals.

## Live / Total Vision (bridge extension)
When the Full Sensory Bridge (main.py + vision_capture.py client) is running:
- Call `get_current_view()` (available in both the pure MCP server and the mounted bridge MCP).
- This returns the latest live camera or screen frame as ImageContent.
- Use exactly like read_image: study internally, describe findings in text only.
- Start the feeder with: `python vision_capture.py` (webcam) or `SOURCE=screen python vision_capture.py`.
- The bridge also exposes /vision/latest and /ws/video for other consumers (dashboard, Riley tunnel awareness, etc.).
