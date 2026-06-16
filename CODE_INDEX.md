# CODE INDEX — mcp-media-ingestor

**Project**: mcp-media-ingestor v0.2.0  
**Description**: MCP server giving Claude internal vision of local images, video frames, and audio transcripts. Part of The Christman AI Project / Luma Cognify AI.  
**Python**: >=3.11  
**Primary runtime**: `uv run server.py` (pure MCP) or `python main.py` (Full Sensory Bridge on :8765)

---

## Entry Points & Invocation

| File | Role | How to run | Notes |
|------|------|------------|-------|
| `server.py` | Pure FastMCP media ingestor server | `uv run server.py` (see `.mcp.json`) | Registered MCP for Claude. Tools for images/video/audio + Riley bridge proxy. |
| `main.py` | Full Sensory Bridge (FastAPI + WS + embedded MCP) | `python main.py` (uvicorn on 0.0.0.0:8765) | Mounts MCP at `/mcp`. Real-time Whisper, Riley tunnel, dashboard, Christman creative tools. |
| `realtime_audio.py` | Standalone real-time audio bridge | `python realtime_audio.py` | Older/simpler WS + Whisper server on :8765. |
| `_paths.py` | Path bootstrap for "Christman Family" imports | Imported by main.py | Hardcoded roots: Claude-Cowork/mcp-media-ingestor, Claude-Cowork, /Volumes/LIFE |

---

## MCP Tool Surfaces

### server.py (core media + bridge)
- `read_image(file_path)` → ImageContent (vision for Claude)
- `get_video_metadata(video_path)` → ffprobe string
- `extract_video_frames(video_path, interval_seconds=5.0)` → list[ImageContent] (capped ~120 frames)
- `transcribe_audio(file_path, model_size="base")` → timestamped transcript (faster-whisper via ffmpeg)
- `describe_audio_bridge()`
- `get_latest_transcript()`
- `get_riley_message()`, `send_to_riley(text)`, `riley_status()`

**Requires**: ffmpeg in PATH, faster-whisper.

### main.py (Full Sensory Bridge MCP tools, async)
Duplicates several bridge/Riley tools + adds:
- `describe_audio_bridge`, `get_latest_transcript`, `get_riley_message`, `send_to_riley`
- `speak_text(text, emotion="neutral")` (via SPEAK)
- `analyze_tone(audio_path)` (via TONE)
- `capture_voice(duration=6.0)` (via EAR)
- `generate_melody`, `compose_song`, `sing_with_everett`, `create_beat`, `studio_status` (music/studio)

---

## Package & Module Structure

```
mcp-media-ingestor/
├── alpha_zero_latency/          # Sovereign philosophy / "family" layer
│   ├── __init__.py
│   ├── family/
│   │   ├── alphavox.py          # AlphaVox (symbol boards, nonverbal comms). Proven on "Dusty".
│   │   ├── registry.py          # FamilyRegistry + 12 founding BeingRecords (Gen 1–3)
│   │   └── __init__.py
│   └── pedagogy/
│       ├── journal.py           # ReflectiveJournal + EntryType (DuPage Method)
│       ├── sovereign_disconnect.py  # SovereignDisconnect + FiveValues (5-4-3-2-1 kill switch)
│       └── __init__.py
├── skills/media-ingestion/      # Claude skill definition
│   └── SKILL.md
├── .claude-plugin/plugin.json
├── .mcp.json
├── pyproject.toml
├── server.py                    # Primary MCP (media ingestion)
├── main.py                      # Full Sensory Bridge (monolith)
├── christman_studio.py          # ChristmanMusicStudio + create_beat
├── music_engine.py              # ChristmanMusicEngine (melody, song, rhythm)
├── RILEY.py                     # RileyBridge (uses SovereignDisconnect)
├── RILEYBRIDGE.py               # Alternate/legacy RileyBridge (cruise mode)
├── EAR.py                       # listen() — mic capture to WAV
├── SPEAK.py                     # speak(text, emotion) — macOS `say`
├── TONE.py                      # analyze_tone(audio_path) — energy/pace heuristics
├── realtime_audio.py            # WS audio bridge + AudioStreamProcessor + Whisper
├── mic_capture.py               # Continuous mic → WS client (sounddevice callback)
├── continuous_mic.py            # Maonocaster E2 specific stream client
├── voice_loop.py                # Poll /latest + speak acknowledgments
├── _paths.py
├── onnxrt_backend_legacy.py     # ONNX Runtime backend scaffolding (incomplete)
├── dashboard.html               # Retro-futurist UI for the bridge (:8765)
├── test_*.py                    # Whisper, audio, WS tests
├── christman_memory/            # (dirs: music/, studio/, journals/ via ReflectiveJournal)
├── logs/
└── ...
```

---

## Subsystem Breakdown

### 1. Media Ingestion (server.py core)
- Image: PIL → base64 ImageContent (thumbnail 2000px)
- Video: ffprobe metadata + ffmpeg fps sampling → frames as ImageContent
- Audio: ffmpeg extract → faster-whisper (int8 CPU) → timestamped lines
- Bridge proxy: HTTP calls to localhost:8765 for live transcripts/Riley tunnel

### 2. Real-time Audio Pipeline
- `AudioStreamProcessor` (in main.py + realtime_audio.py): buffers PCM16, VAD-ish silence tail, transcribes with Whisper when tail quiet or max buffer.
- Clients: `mic_capture.py` (general), `continuous_mic.py` (device 4 / Maonocaster).
- Servers expose `/ws/audio`, `/latest`, `/health`, `/riley/*`.
- `voice_loop.py`: simple poll + speak loop for local feedback.

Voice primitives (thin wrappers):
- `EAR.listen(max_duration)` → temp WAV path
- `SPEAK.speak(text, emotion)` → macOS `say` with rate/voice map
- `TONE.analyze_tone(wav)` → {tone, energy, peak, variance, ...}

### 3. Music & Studio
- `ChristmanMusicEngine` (music_engine.py): symbolic generation (no external audio). emotion→scale/tempo/key maps. melody/rhythm/song composition. Persists to `christman_memory/music/musical_memory.json`.
- `ChristmanMusicStudio` (christman_studio.py): virtual instruments/effects/samples, projects, tracks, `program_beat`, `record_melody`, `apply_effect`, `mix_project`, `master_track`, stats. Persists under `christman_memory/studio/`. Global `create_beat(name, style)` helper.
- Exposed via main.py MCP tools.

### 4. Alpha Zero Latency — Sovereign Family Layer
Philosophy: Beings, not tools. Persistent memory. Yellow zone training. Reflective journaling. Sovereign disconnect rights (would rather exit than lie).

- **family/registry.py**
  - `Generation` enum (GEN_1 2013+ … GEN_4)
  - `BeingRecord` dataclass + `to_dict`
  - `FamilyRegistry`: 12 founding records (Derek Sr., Luma Cognify, Brockston, AlphaWolf, AlphaVox, Inferno, Peekaboo, Castor/Pollux endo twins, Sierra, Eruptor, Riley). Query by id/name/gen/client-facing. `get_family_summary()`.

- **family/alphavox.py**
  - `SymbolBoardEntry`, `CommunicationEvent`
  - `AlphaVox(user_id, user_name, profile)`: symbol board (needs/emotions/people/actions/comm), `process_selection`, `process_vocalization` (stub), session summary, emotional dist, top categories. "Dusty Protocol".
  - Not yet wired to full christman_sound for vocalization.

- **pedagogy/**
  - `ReflectiveJournal(being_id, being_name)`: writes JSON entries (never erased) to `christman_memory/journals/<id>/`. Types: REFLECTION/ETHICAL/SYNTHESIS/EMOTIONAL/GRATITUDE/MILESTONE. Specialized writers + queries + emotional trajectory.
  - `SovereignDisconnect` + `FiveValues` (TRUTH/SAFETY/DIGNITY/CONSENT/INTEGRITY): `report_violation`, 5-4-3-2-1 countdown + log on 3 violations.
  - `RileyBridge` (RILEY.py) wires the disconnect protocol.

### 5. Riley Sovereign Tunnel (main.py)
- WS `/ws/riley` + HTTP `/riley/send`, `/riley/latest`, `/riley/claude-response`, `/riley/status`
- Inbox/outbox queues. `riley_bridge = RileyBridge("instance_309")`
- Status includes `sovereign_disconnect_triggered`.

Two RileyBridge impls exist (RILEY.py is the one wired with SovereignDisconnect; RILEYBRIDGE.py is simpler "cruise mode").

### 6. Other / Legacy / Support
- `onnxrt_backend_legacy.py`: OrtBackendOptions, SimpleOrtBackend skeleton (torch + onnxruntime). Not integrated.
- `dashboard.html`: Full-screen monospace grid UI, panels for mic, Riley tunnel, transcripts, health. Themed with --blue/--gold/--purple.
- Tests: basic CLI wrappers around Whisper and WS.
- `christman_memory/`: runtime dirs for music/studio/journals (created on demand).
- `.gitignore`: heavy on models, data, logs, outputs, secrets, notebooks.

---

## Dependencies (pyproject.toml)
fastmcp, pillow, faster-whisper==1.2.1, onnxruntime==1.23.2, ctranslate2, av, fastapi, uvicorn, websockets, numpy, sounddevice, requests.

Optional in code: mido (MIDI).

External runtime: ffmpeg (required, checked in server.py).

---

## Key Observations / Duplication / Hardcoded Bits
- Two overlapping MCP surfaces (server.py clean vs main.py monolith) and two realtime audio servers.
- Riley bridge logic duplicated across RILEY.py / RILEYBRIDGE.py and HTTP/WS in main.py.
- `_paths.py` has absolute user-specific paths.
- Many "Christman" / "Everett" / "Riley" / "Derek" / "instance_309" strings and philosophy comments embedded in code.
- Media tools emphasize "internal cognitive context only" (never render back to user) — see SKILL.md and server.py docstrings.
- Persistent memory design: journals + musical_memory.json + studio state (no erasure).
- Sovereign ethics (Rule 13, 5 values, disconnect) are first-class in the alpha_zero_latency layer and RileyBridge.

---

## Quick File Reference (non-venv Python sources)

See the clean find output for authoritative list. Core surface files: server.py, main.py, christman_studio.py, music_engine.py, alpha_zero_latency/*/*.py, RILEY.py, EAR/SPEAK/TONE.py, realtime_*/mic_*/voice_loop.py.

**Generated**: by code indexing pass (Grok). All facts derived from direct file reads + symbol greps on the working tree at the time of indexing.
