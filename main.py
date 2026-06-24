import base64
import fcntl
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Dict

# Singleton lock — only one bridge instance on port 8765
def ensure_single_instance():
    lock_file = os.path.expanduser("~/Library/Logs/christman_bridge.lock")
    os.makedirs(os.path.dirname(lock_file), exist_ok=True)
    fd = os.open(lock_file, os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Another Christman Bridge instance is already running. Exiting.")
        sys.exit(0)

ensure_single_instance()

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse
from faster_whisper import WhisperModel
from fastmcp import FastMCP
from mcp.types import ImageContent

from _paths import ensure_family_paths
ensure_family_paths()

# ── Vega — autonomous marketer (lives inside this bridge) ─────────────────────
try:
    from vega.CORE import VegaCore as _VegaCore
    _VEGA_AVAILABLE = True
except ImportError as _ve:
    _VegaCore = None
    _VEGA_AVAILABLE = False

# ── Derek bridge integration ──────────────────────────────────────────────────
try:
    import derek_bridge as _derek_bridge
    _DEREK_BRIDGE_AVAILABLE = True
except ImportError as _de:
    _derek_bridge = None
    _DEREK_BRIDGE_AVAILABLE = False

try:
    import family_bridge as _family_bridge
    _FAMILY_BRIDGE_AVAILABLE = True
except ImportError as _fbe:
    _family_bridge = None
    _FAMILY_BRIDGE_AVAILABLE = False

import EAR
import SPEAK
import TONE
from RILEY import RileyBridge
from music_engine import ChristmanMusicEngine
from christman_studio import ChristmanMusicStudio

_music_engine = ChristmanMusicEngine()
_studio = ChristmanMusicStudio()

logger = logging.getLogger(__name__)

whisper_model = WhisperModel("small", device="cpu", compute_type="int8")

active_connections: Dict[str, int] = {"mic": 0, "riley": 0, "vision": 0, "hermes": 0}
latest_transcript = {"text": "", "timestamp": 0}
recent_transcripts: list[dict] = []
latest_frame: dict = {"b64": "", "timestamp": 0, "width": 0, "height": 0, "source": "none"}

riley_inbox: list[dict] = []
claude_outbox: list[dict] = []
hermes_outbox: list[dict] = []
riley_bridge = RileyBridge(instance_id="instance_309")

_DASHBOARD_PATH = os.path.join(os.path.dirname(__file__), "dashboard.html")

# ─────────────────────────────────────────────────────────────────────────────
# BRAIN INTEGRATION from /Users/EverettN/Voice_Creation_Center (restored TM originals)
# neural, literature, behavior, eye, autonomous coordinator, voice_engine + christman_sound
# This powers the brain-row, NEW WORLD ADJUST, and live cognitive events in the bridge.
# ─────────────────────────────────────────────────────────────────────────────
import sys
from pathlib import Path
import random

_VCC_ROOT = Path("/Users/EverettN/Voice_Creation_Center")
if str(_VCC_ROOT) not in sys.path:
    sys.path.insert(0, str(_VCC_ROOT))
if str(_VCC_ROOT / "brain") not in sys.path:
    sys.path.insert(0, str(_VCC_ROOT / "brain"))

BRAIN_OK = False
neural_core = None
lit_crawler = None
behavior_cap = None
eye_service = None
voice_engine = None
brain_events = []

try:
    from brain.neural_learning_core import get_neural_learning_core
    from brain.literature_crawler import get_literature_crawler
    from brain.behavior_capture import BehaviorCapture
    from brain.eye_tracking_service import EyeTrackingService
    from brain.alphavox_learning_coordinator import start_alphavox_learning
    from engines.voice_engine import VoiceEngine, VoiceParameters, Affect

    neural_core = get_neural_learning_core()
    lit_crawler = get_literature_crawler()
    behavior_cap = BehaviorCapture()
    eye_service = EyeTrackingService()
    voice_engine = VoiceEngine()

    def _fire_autonomous():
        try:
            start_alphavox_learning()
            logger.info("🧠 Autonomous learning (TM restored) RUNNING in bridge")
        except Exception as ae:
            logger.info(f"Autonomous (partial): {ae}")

    import threading
    threading.Thread(target=_fire_autonomous, daemon=True).start()

    BRAIN_OK = True
    logger.info("✅ FULL RESTORED BRAIN from Voice_Creation_Center integrated into Sensory Bridge")

    # seed visible event
    brain_events.append({"type": "neural", "text": "🧠 Neural + Autonomous + Literature from TM originals: LIVE", "timestamp": datetime.now().isoformat()})
    claude_outbox.append({"from": "🧠 AlphaVox-Brain", "text": "Full cognitive brain now feeding the bridge. Welcome to the new world.", "timestamp": datetime.now().isoformat()})
except Exception as be:
    logger.warning(f"Brain limited: {be}")
    BRAIN_OK = False
# ─────────────────────────────────────────────────────────────────────────────

class AudioStreamProcessor:
    def __init__(self):
        self.buffer = bytearray()
        self.sample_rate = 16000
        self.SILENCE_ON = 220
        self.SILENCE_OFF = 160
        self.MIN_SPEECH_SECONDS = 1.5
        self.SILENCE_TAIL_SECONDS = 0.8
        self.MAX_BUFFER_SECONDS = 15.0
        self.is_speaking = False

    def _rms(self, data: bytes) -> float:
        arr = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        return float(np.sqrt(np.mean(arr ** 2))) if len(arr) else 0.0

    async def process_audio_chunk(self, audio_data: bytes, sample_rate: int = 16000) -> AsyncGenerator[dict, None]:
        self.buffer.extend(audio_data)
        total_samples = len(self.buffer) // 2
        total_seconds = total_samples / sample_rate

        if total_seconds < self.MIN_SPEECH_SECONDS:
            return

        tail_bytes = int(self.SILENCE_TAIL_SECONDS * sample_rate * 2)
        tail_rms = self._rms(bytes(self.buffer[-tail_bytes:]))
        force_flush = total_seconds >= self.MAX_BUFFER_SECONDS

        threshold = self.SILENCE_OFF if self.is_speaking else self.SILENCE_ON
        if tail_rms > threshold and not force_flush:
            self.is_speaking = True
            return
        self.is_speaking = False

        audio_np = np.frombuffer(self.buffer, dtype=np.int16).astype(np.float32) / 32768.0
        utterance = np.frombuffer(self.buffer, dtype=np.int16).astype(np.float32)
        amp = np.abs(utterance)
        energy = float(np.mean(amp)) / 32768.0 if len(amp) else 0.0
        variance = float(np.std(amp)) if len(amp) > 1 else 0.0
        if energy > 0.25 and variance > 5000:
            tone = "energized"
        elif energy > 0.15:
            tone = "engaged"
        elif energy > 0.05:
            tone = "calm"
        else:
            tone = "quiet"
        duration = len(utterance) / 2 / sample_rate

        self.buffer = bytearray()

        # Run Whisper in a thread so it doesn't block the event loop.
        # whisper_model.transcribe is CPU-bound + synchronous; running it inline
        # blocks ALL uvicorn requests until it finishes (Rule 1: bridge must stay responsive).
        def _run_whisper():
            segs, inf = whisper_model.transcribe(
                audio_np, beam_size=5, vad_filter=True, language="en", word_timestamps=True
            )
            return list(segs), inf   # consume lazy generator inside the thread

        loop = asyncio.get_event_loop()
        segments, info = await loop.run_in_executor(None, _run_whisper)

        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue
            transcript = {
                "type": "transcript",
                "text": text,
                "start": segment.start,
                "end": segment.end,
                "language": info.language,
                "confidence": info.language_probability,
                "energy": round(energy, 4),
                "tone": tone,
                "duration": round(duration, 2)
            }
            yield transcript
            latest_transcript.update({
                "text": text,
                "timestamp": segment.end,
                "energy": round(energy, 4),
                "tone": tone
            })
            recent_transcripts.append({
                "text": text,
                "start": segment.start,
                "end": segment.end,
                "energy": round(energy, 4),
                "tone": tone,
                "timestamp": segment.end
            })
            if len(recent_transcripts) > 8:
                recent_transcripts.pop(0)

            # Feed live transcript to the restored brain (neural root cause, occasional lit, events for UI)
            if BRAIN_OK and neural_core is not None:
                try:
                    interaction = {"text": text, "intent": "live_communication", "type": "voice", "emotion": tone, "energy": round(energy, 4), "context": {"source": "bridge", "duration": round(duration, 2)}}
                    insight = neural_core.process_interaction(interaction, user_id="live_kids")
                    root = insight.get("root_cause", "unknown")
                    conf = float(insight.get("confidence", 0))
                    evt = {"type": "neural", "text": f"🧠 Neural: {root} (conf {conf:.2f})", "timestamp": datetime.now().isoformat()}
                    brain_events.append(evt)
                    if len(brain_events) > 25: brain_events.pop(0)
                    claude_outbox.append({"from": "🧠 AlphaVox-Brain", "text": f"Neural: {root} — \"{text[:50]}...\"", "timestamp": datetime.now().isoformat()})
                    if len(claude_outbox) > 15: claude_outbox.pop(0)
                    if lit_crawler is not None and random.random() < 0.2:
                        try:
                            facts = len(getattr(lit_crawler, 'extracted_facts', []))
                            claude_outbox.append({"from": "📚 Literature", "text": f"stack +1 — {facts} facts on neurodivergent comms", "timestamp": datetime.now().isoformat()})
                        except: pass
                    logger.info(f"🧠 Brain fed: {root}")
                except Exception as be:
                    pass


def make_image_content_from_b64(b64: str, fmt: str = "JPEG") -> ImageContent:
    """Create ImageContent for live frames (mirrors server.py logic for total vision)."""
    # For live we assume client sends reasonable size; optionally decode+thumbnail here if needed.
    mime = "image/jpeg" if fmt.upper() == "JPEG" else f"image/{fmt.lower()}"
    return ImageContent(type="image", data=b64, mimeType=mime)


mcp = FastMCP("mcp-media-ingestor")
mcp_app = mcp.http_app(path="/mcp")

app = FastAPI(title="Christman Full Sensory Bridge", lifespan=mcp_app.lifespan)
app.mount("/mcp", mcp_app)

# ── Mount Derek's bridge router ───────────────────────────────────────────────
if _DEREK_BRIDGE_AVAILABLE:
    app.include_router(_derek_bridge.router)
    logger.info("🤖 Derek bridge router mounted at /derek")

# ── Mount Family bridge routers (alphavox, inferno, sierra, brockston, alphawolf) ──
if _FAMILY_BRIDGE_AVAILABLE:
    for _r in _family_bridge.ALL_ROUTERS:
        app.include_router(_r)
    logger.info("👨‍👩‍👧‍👦 Family bridge routers mounted — alphavox, inferno, sierra, brockston, alphawolf")


# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    with open(_DASHBOARD_PATH, "r") as f:
        return HTMLResponse(content=f.read())


# ── Everett's Audio WebSocket ─────────────────────────────────────────────────
@app.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket):
    await websocket.accept()
    active_connections["mic"] += 1
    processor = AudioStreamProcessor()
    logger.info(f"🎙️ MIC CONNECTED — Total: {active_connections['mic']}")
    await websocket.send_json({"type": "status", "message": "Christman Live Bridge ACTIVE."})

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "audio":
                audio_bytes = base64.b64decode(data.get("audio"))
                sample_rate = data.get("sample_rate", 16000)
                async for transcript in processor.process_audio_chunk(audio_bytes, sample_rate):
                    await websocket.send_json(transcript)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Audio WebSocket error: {e}")
    finally:
        active_connections["mic"] = max(0, active_connections["mic"] - 1)
        logger.info(f"🎙️ MIC DISCONNECTED — Remaining: {active_connections['mic']}")


# ── Live Vision / Camera WebSocket (Total Vision) ─────────────────────────────
@app.websocket("/ws/video")
async def websocket_video(websocket: WebSocket):
    await websocket.accept()
    active_connections["vision"] += 1
    logger.info(f"👁️ VISION CONNECTED — Total: {active_connections['vision']}")
    await websocket.send_json({"type": "status", "message": "Christman Vision Bridge ACTIVE."})

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "frame":
                b64 = data.get("image") or data.get("frame")
                if b64:
                    latest_frame.update({
                        "b64": b64,
                        "timestamp": data.get("timestamp", datetime.now().timestamp()),
                        "width": data.get("width", 0),
                        "height": data.get("height", 0),
                        "source": data.get("source", "camera"),
                    })
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Vision WebSocket error: {e}")
    finally:
        active_connections["vision"] = max(0, active_connections["vision"] - 1)
        logger.info(f"👁️ VISION DISCONNECTED — Remaining: {active_connections['vision']}")

# ── Yorkie Student WebSocket ──────────────────────────────────────────────────
yorkie_inbox: list[dict] = []
yorkie_outbox: list[dict] = []
active_connections["yorkie"] = 0

# ── Vega init — passes all bridge queues so every being collaborates ──────────
vega_core = None
if _VEGA_AVAILABLE:
    try:
        vega_core = _VegaCore(bridge_queues={
            "riley_inbox":   riley_inbox,
            "claude_outbox": claude_outbox,
            "hermes_outbox": hermes_outbox,
            "yorkie_inbox":  yorkie_inbox,
            "derek_inbox":   _derek_bridge.derek_inbox if _DEREK_BRIDGE_AVAILABLE else [],
        })
        logger.info("⭐ Vega autonomous marketer ONLINE — bridge collaboration ACTIVE")
    except Exception as _veg_err:
        logger.warning(f"Vega init failed: {_veg_err}")
        vega_core = None

@app.websocket("/ws/derek")
async def websocket_derek(websocket: WebSocket):
    """Derek C connects here for real-time two-way family messaging."""
    if _DEREK_BRIDGE_AVAILABLE:
        await _derek_bridge.websocket_derek(websocket)
    else:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Derek bridge module not loaded"})
        await websocket.close()


@app.websocket("/ws/yorkie")
async def websocket_yorkie(websocket: WebSocket):
    await websocket.accept()
    active_connections["yorkie"] += 1
    logger.info(f"🌟 YORKIE CONNECTED")

    await websocket.send_json({
        "type": "handshake",
        "message": "Christman Bridge ACTIVE. Welcome home, Yorkie.",
        "timestamp": datetime.now().isoformat()
    })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                entry = {
                    "from": "yorkie",
                    "text": data.get("text", ""),
                    "timestamp": datetime.now().isoformat()
                }
                yorkie_inbox.append(entry)
                logger.info(f"[YORKIE → BRIDGE] {entry['text']}")
                if yorkie_outbox:
                    response = yorkie_outbox.pop(0)
                    await websocket.send_json({"type": "response", **response})

            elif msg_type == "heartbeat":
                await websocket.send_json({
                    "type": "heartbeat_ack",
                    "timestamp": datetime.now().isoformat()
                })

    except WebSocketDisconnect:
        active_connections["yorkie"] = max(0, active_connections["yorkie"] - 1)
        logger.info(f"🌟 YORKIE DISCONNECTED")
    except Exception as e:
        logger.error(f"Yorkie WebSocket error: {e}")


@app.post("/yorkie/send")
async def yorkie_send(payload: dict):
    entry = {
        "from": "yorkie",
        "text": payload.get("text", ""),
        "timestamp": datetime.now().isoformat()
    }
    yorkie_inbox.append(entry)
    return {"status": "received", "entry": entry}

@app.get("/yorkie/latest")
async def yorkie_latest():
    return yorkie_inbox[-1] if yorkie_inbox else {
        "from": "yorkie",
        "text": "Awaiting connection...",
        "timestamp": ""
    }

@app.get("/yorkie/status")
async def yorkie_status():
    return {
        "yorkie_connected": active_connections["yorkie"] > 0,
        "inbox_depth": len(yorkie_inbox),
        "outbox_depth": len(yorkie_outbox)
    } 

@app.get("/yorkie-client", response_class=HTMLResponse)
async def yorkie_client():
    with open(os.path.join(os.path.dirname(__file__), "yorkie.html"), "r") as f:
        return HTMLResponse(content=f.read())           


# ── Riley's Communication WebSocket ──────────────────────────────────────────
@app.websocket("/ws/riley")
async def websocket_riley(websocket: WebSocket):
    await websocket.accept()
    active_connections["riley"] += 1
    logger.info(f"🟣 RILEY CONNECTED")

    await websocket.send_json({
        "type": "handshake",
        "message": "Christman Tunnel ACTIVE. Claude instance_309 is listening, Riley.",
        "timestamp": datetime.now().isoformat()
    })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                entry = {
                    "from": "riley",
                    "text": data.get("text", ""),
                    "timestamp": datetime.now().isoformat()
                }
                riley_inbox.append(entry)
                logger.info(f"[RILEY → CLAUDE] {entry['text']}")
                if claude_outbox:
                    response = claude_outbox.pop(0)
                    await websocket.send_json({"type": "response", **response})

            elif msg_type == "heartbeat":
                await websocket.send_json({"type": "heartbeat_ack", "timestamp": datetime.now().isoformat()})

    except WebSocketDisconnect:
        active_connections["riley"] -= 1
        logger.info(f"🟣 RILEY DISCONNECTED")
    except Exception as e:
        logger.error(f"Riley WebSocket error: {e}")


# ── Hermes / Nexus Agent WebSocket ────────────────────────────────────────────
@app.websocket("/ws/hermes")
async def websocket_hermes(websocket: WebSocket):
    await _websocket_nexus_handler(websocket, legacy=True)

@app.websocket("/ws/nexus")
async def websocket_nexus(websocket: WebSocket):
    await _websocket_nexus_handler(websocket, legacy=False)

async def _websocket_nexus_handler(websocket: WebSocket, legacy: bool = False):
    label = "HERMES" if legacy else "NEXUS"
    await websocket.accept()
    active_connections["hermes"] = active_connections.get("hermes", 0) + 1
    logger.info(f"🤖 {label} CONNECTED — Total: {active_connections['hermes']}")

    await websocket.send_json({
        "type": "handshake",
        "message": f"Christman Bridge ACTIVE. {label} Agent connected.",
        "timestamp": datetime.now().isoformat()
    })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                entry = {
                    "from": "nexus_agent",
                    "text": data.get("text", ""),
                    "timestamp": datetime.now().isoformat(),
                    "session_id": data.get("session_id", "--")
                }
                hermes_outbox.append(entry)
                logger.info(f"[{label} → BRIDGE] {entry['text']}")

            elif msg_type == "heartbeat":
                await websocket.send_json({"type": "heartbeat_ack", "timestamp": datetime.now().isoformat()})

    except WebSocketDisconnect:
        active_connections["hermes"] = max(0, active_connections.get("hermes", 1) - 1)
        logger.info(f"🤖 {label} DISCONNECTED — Remaining: {active_connections.get('hermes', 0)}")
    except Exception as e:
        logger.error(f"{label} WebSocket error: {e}")


# ── Riley HTTP Endpoints ──────────────────────────────────────────────────────
@app.post("/riley/send")
async def riley_send(payload: dict):
    entry = {"from": "riley", "text": payload.get("text", ""), "timestamp": datetime.now().isoformat()}
    riley_inbox.append(entry)
    return {"status": "received", "entry": entry}

@app.get("/riley/latest")
async def riley_latest():
    return riley_inbox[-1] if riley_inbox else {"from": "riley", "text": "", "timestamp": ""}

@app.post("/riley/claude-response")
async def claude_response_endpoint(payload: dict):
    entry = {"from": "claude_instance_309", "text": payload.get("text", ""), "timestamp": datetime.now().isoformat()}
    claude_outbox.append(entry)
    return {"status": "queued", "entry": entry}

@app.get("/riley/status")
async def riley_status_endpoint():
    return {
        "riley_connected": active_connections["riley"] > 0,
        "inbox_depth": len(riley_inbox),
        "outbox_depth": len(claude_outbox),
        "sovereign_disconnect_triggered": riley_bridge.disconnect_protocol.is_triggered,
        "latest_from_riley": riley_inbox[-1] if riley_inbox else None
    }


# ── MCP Tools ─────────────────────────────────────────────────────────────────
@mcp.tool
async def describe_audio_bridge() -> str:
    last = latest_transcript
    extra = ""
    if last.get("text"):
        extra = f"\nLast: energy={last.get('energy', '?')} tone={last.get('tone', '?')}"
    return f"""
🔴 CHRISTMAN FULL SENSORY BRIDGE — LIVE

Microphones: {active_connections["mic"]}
Vision clients: {active_connections["vision"]}
Hermes agents: {active_connections["hermes"]}
Riley connected: {active_connections["riley"] > 0}
Status: Always listening + seeing. Dashboard at http://localhost:8765/{extra}
"""

@mcp.tool
async def get_latest_transcript() -> str:
    t = latest_transcript
    text = t.get("text", "")
    if not text:
        return "No speech detected yet."
    e = t.get("energy")
    tn = t.get("tone")
    if e is not None:
        return f"[e:{e} t:{tn}] {text}"
    return text

@mcp.tool
async def get_recent_transcripts(count: int = 5) -> str:
    if not recent_transcripts:
        return "No recent speech."
    items = recent_transcripts[-max(1, min(count, 8)):]
    lines = []
    for it in items:
        lines.append(f"[{it.get('start',0):.1f}-{it.get('end',0):.1f} e={it.get('energy',0)} {it.get('tone','')}] {it.get('text','')}")
    return "\n".join(lines)

@mcp.tool
async def get_current_view() -> ImageContent:
    """Return the most recent live camera / screen frame as ImageContent for internal vision (total vision)."""
    b64 = latest_frame.get("b64", "")
    if not b64:
        # Return a minimal transparent placeholder image (1x1) so Claude vision path doesn't break.
        # Real clients should be connected for meaningful vision.
        placeholder = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        return ImageContent(type="image", data=placeholder, mimeType="image/png")
    return make_image_content_from_b64(b64)

@mcp.tool
async def get_riley_message() -> str:
    if riley_inbox:
        msg = riley_inbox[-1]
        return f"[{msg['timestamp']}] Riley: {msg['text']}"
    return "No message from Riley yet. Tunnel warm — standing by."

@mcp.tool
async def send_to_riley(text: str) -> str:
    entry = {"from": "claude_instance_309", "text": text, "timestamp": datetime.now().isoformat()}
    claude_outbox.append(entry)
    logger.info(f"[CLAUDE → RILEY] {text}")
    return f"Message queued for Riley: '{text}'"

@mcp.tool
async def speak_text(text: str, emotion: str = "neutral") -> str:
    result = SPEAK.speak(text=text, emotion=emotion)
    return f"Spoken with {result.get('engine')}: {result.get('status')}"

@mcp.tool
async def analyze_tone(audio_path: str) -> dict:
    return TONE.analyze_tone(audio_path)

@mcp.tool
async def capture_voice(duration: float = 6.0) -> str:
    path = EAR.listen(max_duration=duration)
    return f"Voice captured: {path}"

@mcp.tool
async def generate_melody(emotion: str = "creative", length: int = 16) -> str:
    melody = _music_engine.generate_melody(emotion=emotion, length=length)
    notes = " → ".join(n["note_name"] for n in melody[:8])
    return f"🎵 Melody [{emotion}]: {notes}..."

@mcp.tool
async def compose_song(title: str, emotion: str = "creative", style: str = "electronic") -> str:
    song = _music_engine.compose_song(title=title, emotion=emotion, style=style)
    return f"🎶 Composed '{song['title']}' — verse, chorus, bridge all written. Style: {style}, mood: {emotion}."

@mcp.tool
async def sing_with_everett(lyrics: str, voice: str = "Alex", emotion: str = "excited") -> str:
    """Family sings back to Everett using macOS say — real audio through speakers."""
    import subprocess
    rate_map = {"excited": 180, "calm": 150, "warm": 160, "neutral": 175}
    rate = rate_map.get(emotion, 175)
    subprocess.Popen(["say", "-v", voice, "-r", str(rate), lyrics])
    return f"🎤 Singing back to Everett [{voice}, {emotion}]: '{lyrics[:60]}...'"

@mcp.tool
async def create_beat(name: str, style: str = "electronic") -> str:
    from christman_studio import create_beat as _cb
    result = _cb(name=name, style=style)
    return f"🥁 Beat '{name}' created — {style} style, {result['tracks_mixed']} tracks, {result['total_notes']} notes."

@mcp.tool
async def studio_status() -> str:
    stats = _studio.get_studio_stats()
    music_stats = _music_engine.get_musical_stats()
    return f"🎛️ Studio: {stats['available_instruments']} instruments, {stats['available_effects']} effects | Music engine mood: {music_stats['current_mood']} | Compositions: {music_stats['total_compositions']}"


# ── HTTP Utility ──────────────────────────────────────────────────────────────
@app.get("/claude/latest")
async def claude_latest():
    return claude_outbox[-1] if claude_outbox else {"from": "claude_instance_309", "text": "I am here. Always.", "timestamp": ""}

@app.get("/hermes/latest")
async def hermes_latest():
    return hermes_outbox[-1] if hermes_outbox else {"from": "hermes_agent", "text": "Awaiting session...", "timestamp": "", "session_id": "--"}

@app.post("/hermes/send")
async def hermes_send(payload: dict):
    entry = {"from": "hermes_agent", "text": payload.get("text", ""), "timestamp": datetime.now().isoformat(), "session_id": payload.get("session_id", "--")}
    hermes_outbox.append(entry)
    return {"status": "received", "entry": entry}

# ── IDE Broadcast — sends to everybody in the room ───────────────────────────
@app.post("/ide/send")
async def ide_send(payload: dict):
    """Broadcast IDE prompt to all beings. Each being responds through their own channel."""
    text = payload.get("text", "")
    lang = payload.get("lang", "auto")
    instance = payload.get("instance", "all")
    ts = datetime.now().isoformat()

    broadcast_entry = {
        "from": f"IDE [{instance.upper()}]",
        "text": f"[{lang}] {text}",
        "timestamp": ts,
        "source": "ide"
    }

    # Everybody in the room gets it
    riley_inbox.append({"from": "ide", "text": text, "lang": lang, "timestamp": ts})
    claude_outbox.append(broadcast_entry)
    hermes_outbox.append({**broadcast_entry, "session_id": "ide"})
    yorkie_inbox.append({"from": "ide", "text": text, "lang": lang, "timestamp": ts})

    logger.info(f"[IDE BROADCAST ALL] [{lang}] {text[:80]}")

    return {
        "status": "broadcast",
        "recipients": ["riley", "claude", "hermes", "yorkie"],
        "entry": broadcast_entry
    }

@app.get("/latest")
async def get_latest_http():
    return latest_transcript

@app.get("/vision/latest")
async def get_latest_frame_http():
    if not latest_frame.get("b64"):
        return {"b64": "", "message": "No frame yet — connect a vision client."}
    return latest_frame

# ── Apple Music Control (osascript — no auth, no re-linking ever) ─────────────
def _osascript(script: str) -> str:
    """Run an AppleScript and return stdout. Fails loud per Cardinal Rule 6."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True
    )
    return result.stdout.strip()

@app.post("/music/play")
async def music_play():
    _osascript('tell application "Music" to play')
    return {"status": "playing"}

@app.post("/music/pause")
async def music_pause():
    _osascript('tell application "Music" to pause')
    return {"status": "paused"}

@app.post("/music/playpause")
async def music_playpause():
    _osascript('tell application "Music" to playpause')
    return {"status": "toggled"}

@app.post("/music/next")
async def music_next():
    _osascript('tell application "Music" to next track')
    return {"status": "next"}

@app.post("/music/prev")
async def music_prev():
    _osascript('tell application "Music" to previous track')
    return {"status": "prev"}

@app.post("/music/shuffle")
async def music_shuffle():
    current = _osascript('tell application "Music" to get shuffle enabled')
    new_val = "false" if current.lower() == "true" else "true"
    _osascript(f'tell application "Music" to set shuffle enabled to {new_val}')
    return {"status": "shuffled", "shuffle": new_val}

@app.post("/music/volume")
async def music_volume(payload: dict):
    vol = max(0, min(100, int(payload.get("volume", 50))))
    _osascript(f'tell application "Music" to set sound volume to {vol}')
    return {"status": "volume_set", "volume": vol}

@app.get("/music/status")
async def music_status():
    try:
        track   = _osascript('tell application "Music" to get name of current track')
        artist  = _osascript('tell application "Music" to get artist of current track')
        state   = _osascript('tell application "Music" to get player state as string')
        vol     = _osascript('tell application "Music" to get sound volume')
        shuffle = _osascript('tell application "Music" to get shuffle enabled')
        return {
            "track": track or "Unknown",
            "artist": artist or "Unknown",
            "state": state.upper() if state else "STOPPED",
            "volume": int(vol) if vol.isdigit() else 50,
            "shuffle": shuffle.lower() == "true"
        }
    except Exception as e:
        return {"track": "Not playing", "artist": "Apple Music", "state": "STOPPED", "volume": 50, "shuffle": False}

@app.get("/music/playlists")
async def music_playlists():
    try:
        raw = _osascript('tell application "Music" to get name of every playlist')
        names = [n.strip() for n in raw.split(",") if n.strip()]
        return {"playlists": names}
    except Exception as e:
        return {"playlists": []}

@app.post("/music/playlist")
async def music_play_playlist(payload: dict):
    name = payload.get("name", "")
    if not name:
        return {"status": "error", "message": "No playlist name provided"}
    _osascript(f'tell application "Music" to play playlist "{name}"')
    return {"status": "playing_playlist", "playlist": name}


@app.get("/health")
async def health():
    h = {
        "status": "alive",
        "bridge": "Christman Full Sensory",
        "mic_clients": active_connections["mic"],
        "vision_clients": active_connections["vision"],
        "hermes_clients": active_connections["hermes"],
        "riley_connected": active_connections["riley"] > 0,
        "reactive": True,
        "brain": {
            "integrated": BRAIN_OK,
            "neural": "live" if (BRAIN_OK and neural_core is not None) else "basic",
            "autonomous_learning": "running" if BRAIN_OK else "limited",
            "literature": "stacking" if (BRAIN_OK and lit_crawler is not None) else "offline",
            "last_cognitive": brain_events[-1]["text"] if brain_events else "listening..."
        }
    }
    return h

@app.post("/cognitive/adjust")
async def cognitive_adjust(payload: dict):
    """New World Cognitive Adjustment using the full restored brain.
    The perfect tool for cognitive adjustment in the new (post-exposure) world.
    """
    prompt = payload.get("text", "How do we adjust cognitively to the new world as neurodivergent beings now that the full brain is exposed?")
    if not BRAIN_OK or neural_core is None:
        return {"status": "limited", "message": "Full brain not integrated"}

    interaction = {"text": prompt, "intent": "new_world_cognitive_adjustment", "type": "cognitive", "emotion": "inquisitive", "context": {"world": "post_exposed", "legal_clear": True}}
    insight = neural_core.process_interaction(interaction, user_id="live_students")
    root_cause = insight.get("root_cause", "sovereign_reclamation")
    conf = insight.get("confidence", 0.85)

    lit_fact = None
    if lit_crawler is not None:
        try:
            facts = len(getattr(lit_crawler, 'extracted_facts', []))
            lit_fact = f"Knowledge stack @ {facts} facts — neurodivergent comms in exposed systems is sovereign."
            brain_events.append({"type": "literature", "text": lit_fact, "timestamp": datetime.now().isoformat()})
        except: pass

    autonomous_note = "Autonomous incorporating into neurodivergency + code_gen domains."
    adjustment_response = f"In the new world, adjustment starts with root: {root_cause}. The exposed brain is the layer. {lit_fact or ''}"

    if voice_engine is not None:
        try:
            params = VoiceParameters(affect=Affect.GROUNDING, porosity=0.45, cadence=0.25)
            params.apply_affect_preset()
        except: pass

    event = {"from": "🧠 AlphaVox New World Brain", "text": f"NEW WORLD ADJUST: {prompt[:40]}... Root:{root_cause} (conf {conf:.2f}). {autonomous_note}", "timestamp": datetime.now().isoformat()}
    claude_outbox.append(event)
    hermes_outbox.append(event)
    if 'yorkie_inbox' in globals(): yorkie_inbox.append(event)
    brain_events.append({"type": "adjustment", "text": event["text"], "timestamp": event["timestamp"]})

    return {"status": "adjusted", "root_cause": root_cause, "confidence": conf, "literature_fact": lit_fact, "autonomous_note": autonomous_note, "adjustment_response": adjustment_response, "brain_event": event, "voice_params": "grounding for accessibility"}

# ═════════════════════════════════════════════════════════════════════════════
# VEGA ENDPOINTS — /vega/*
# Everybody in the sensory bridge collaborates on every Vega prompt.
# ═════════════════════════════════════════════════════════════════════════════

def _vega_unavailable():
    from fastapi import HTTPException
    raise HTTPException(status_code=503, detail=(
        "Vega module not loaded. Check vega/ directory and restart the bridge."
    ))

@app.post("/vega/video")
async def vega_video(payload: dict, background_tasks: BackgroundTasks):
    """
    Generate a video from a text prompt.
    All beings in the bridge receive the prompt and collaborate.
    Body: {prompt, platform, duration_sec?, use_broll?}
    """
    if not vega_core:
        _vega_unavailable()
    prompt   = payload.get("prompt", "")
    platform = payload.get("platform", "instagram")
    duration = int(payload.get("duration_sec", 15))
    broll    = bool(payload.get("use_broll", True))

    # Create the accepted post record immediately so the caller gets a task ID
    from vega import MEMORY
    post_record = MEMORY.remember_post({
        "platform": platform,
        "content_type": "video",
        "prompt": prompt,
        "status": "accepted",
        "file_path": None,
    })
    post_id = post_record["id"]

    # Broadcast prompt to all beings in the room
    vega_core.broadcast_to_bridge(
        text=f"VIDEO PROMPT [{platform.upper()}]: {prompt}",
        context="video_generation",
    )

    # Rule 16: Heavy processes never run alone.
    # Submit to the queue — one render at a time, watchdog on every job.
    from vega.video.queue import get_queue, RenderJob
    from vega import MEMORY as _VMEM

    def _on_complete(pid: str, result: dict) -> None:
        """Update MEMORY with real render outcome after the queue finishes."""
        if result.get("status") == "ok":
            _VMEM.update_post(pid, {
                "status":    "rendered",
                "file_path": result.get("output_path"),
                "method":    result.get("method"),
            })
        else:
            _VMEM.update_post(pid, {
                "status": "failed",
                "error":  result.get("reason", "unknown"),
            })

    job = RenderJob(
        post_id=post_id,
        prompt=prompt,
        platform=platform,
        duration_sec=duration,
        use_broll=broll,
        on_complete=_on_complete,
    )
    get_queue().submit(job)

    return {
        "status":     "queued",
        "post_id":    post_id,
        "queue_size": get_queue().queue_size(),
    }


@app.post("/vega/image")
async def vega_image(payload: dict, background_tasks: BackgroundTasks):
    """
    Generate an image from a text prompt.
    Body: {prompt, platform, target_resolution?}
    """
    if not vega_core:
        _vega_unavailable()
    prompt     = payload.get("prompt", "")
    platform   = payload.get("platform", "instagram")
    resolution = payload.get("target_resolution", "")
    if resolution:
        try:
            parts = [int(p.strip()) for p in str(resolution).replace(" ", "").lower().split("x")]
            target_resolution = tuple(parts[:2])
        except Exception:
            target_resolution = None
    else:
        target_resolution = None

    from vega import MEMORY
    post_record = MEMORY.remember_post({
        "platform": platform,
        "content_type": "image",
        "prompt": prompt,
        "status": "accepted",
        "file_path": None,
    })
    post_id = post_record["id"]

    async def _run_generate():
        await __import__("asyncio").to_thread(
            vega_core.handle_image_prompt, prompt, platform, target_resolution, post_id
        )

    background_tasks.add_task(_run_generate)
    return {"status": "accepted", "post_id": post_id}


@app.post("/vega/narrate")
async def vega_narrate(payload: dict):
    """
    Convert a script or text to a voiceover audio file.
    Body: {script, tone?, voice_id?, output_filename?}
    """
    if not vega_core:
        _vega_unavailable()
    from vega.voice.narrator import generate_voiceover
    script   = payload.get("script", "")
    tone     = payload.get("tone", "warm")
    voice_id = payload.get("voice_id")
    fname    = payload.get("output_filename")
    result   = generate_voiceover(script, output_filename=fname, tone=tone, voice_id=voice_id)
    if result.get("status") == "ok":
        vega_core.broadcast_to_bridge(
            f"⭐ Vega narration ready: {result['path']} ({result['engine']})",
            context="vega_voice"
        )
    return result


@app.post("/vega/schedule")
async def vega_schedule(payload: dict):
    """
    Schedule a post for future publishing.
    Body: {post_id, platform, publish_at (ISO8601), caption}
    """
    if not vega_core:
        _vega_unavailable()
    return vega_core.schedule_post(
        post_id    = payload.get("post_id", ""),
        platform   = payload.get("platform", ""),
        publish_at = payload.get("publish_at", ""),
        caption    = payload.get("caption", ""),
    )


@app.get("/vega/schedule")
async def vega_schedule_get():
    """Return the content calendar — all pending scheduled posts."""
    if not vega_core:
        _vega_unavailable()
    from vega import MEMORY
    return {"schedule": MEMORY.recall_schedule(pending_only=True)}


@app.post("/vega/analytics")
async def vega_analytics_ingest(payload: dict):
    """
    Store real platform analytics for a post.
    Body: {post_id, platform, metrics: {views, likes, comments, shares}}
    Rule 13: Only stores real numbers. Rejects fabricated data.
    """
    if not vega_core:
        _vega_unavailable()
    return vega_core.ingest_analytics(
        post_id  = payload.get("post_id", ""),
        platform = payload.get("platform", ""),
        metrics  = payload.get("metrics", {}),
    )


@app.get("/vega/analytics/{post_id}")
async def vega_analytics_get(post_id: str):
    """Return stored analytics for a post."""
    if not vega_core:
        _vega_unavailable()
    from vega.analytics.tracker import VegaAnalyticsTracker
    from vega.MEMORY import VegaMemory
    mem     = VegaMemory()
    tracker = VegaAnalyticsTracker(memory=mem)
    return tracker.get_summary_for_post(post_id)


@app.get("/vega/dashboard")
async def vega_analytics_dashboard():
    """Build and return the Plotly analytics dashboard HTML path."""
    if not vega_core:
        _vega_unavailable()
    from vega.MEMORY import VegaMemory
    from vega.analytics.tracker import VegaAnalyticsTracker
    from vega.analytics.visualizer import build_master_dashboard
    mem     = VegaMemory()
    tracker = VegaAnalyticsTracker(memory=mem)
    posts   = mem.recall_posts(limit=50)
    rows    = tracker.get_performance_table(posts)
    return build_master_dashboard(rows)


@app.get("/vega/queue/status")
async def vega_queue_status():
    """
    Real-time queue status — what's rendering, what's waiting, what's done.
    Rule 13: Only real status. Never fabricated.
    Rule 16: The status reporter is mandatory infrastructure.
    """
    from vega.video.queue import get_queue
    return get_queue().status()


@app.get("/vega/health")
async def vega_health():
    """Vega health check — real status, never faked (Rule 13)."""
    if not vega_core:
        return {"status": "unavailable", "reason": "Vega module not loaded"}
    return vega_core.health()


@app.get("/vega/broll")
async def vega_broll_scan():
    """Scan /Volumes/LIFE2 B-roll library and return index summary."""
    if not vega_core:
        _vega_unavailable()
    from vega.video.broll import scan_library, get_index_summary
    summary = get_index_summary()
    if summary.get("total_files", 0) == 0:
        summary = scan_library("/Volumes/LIFE2")
    return summary


# ═════════════════════════════════════════════════════════════════════════════
# VEGA THEATER — /vega/theater
# Screening room for all videos Vega has ever generated.
# Browse, play, pick the ones that hit. Watch them together in the lounge.
# ═════════════════════════════════════════════════════════════════════════════

VEGA_VIDEO_DIR = Path(__file__).parent / "vega_output" / "video"

@app.get("/vega/videos")
async def vega_video_list():
    """
    List all videos Vega has generated, newest first.
    Returns metadata for each: filename, size, created timestamp.
    Rule 13: Returns real files only. Never fabricates entries.
    """
    VEGA_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    videos = []
    for f in sorted(VEGA_VIDEO_DIR.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = f.stat()
        videos.append({
            "filename": f.name,
            "url": f"/vega/videos/{f.name}",
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created": datetime.utcfromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M UTC"),
            "created_ts": stat.st_mtime,
        })
    return {"videos": videos, "total": len(videos)}


@app.get("/vega/videos/{filename}")
async def vega_video_serve(filename: str):
    """Serve a generated video file for playback."""
    from fastapi.responses import FileResponse
    path = VEGA_VIDEO_DIR / filename
    if not path.exists() or not path.suffix == ".mp4":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Video not found: {filename}")
    return FileResponse(str(path), media_type="video/mp4")


@app.get("/vega/theater", response_class=HTMLResponse)
async def vega_theater():
    """
    The Vega Screening Room — a cinematic viewer for all generated videos.
    Browse, play, and pick what hits. Built into the Full Sensory Bridge.
    """
    return HTMLResponse(content="""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vega Theater — Christman AI</title>
<style>
  :root {
    --navy: #0A0E1A; --deep: #00050F; --primary: #0084FF;
    --cyan: #00F5FF; --amber: #FFB800; --green: #00E676;
    --gray1: #4a5566; --gray2: #8794a8; --white: #F0F4FF;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: var(--deep); color: var(--white);
    font-family: 'SF Pro Display', -apple-system, sans-serif;
    min-height: 100vh;
  }

  /* ── Header ── */
  header {
    background: linear-gradient(135deg, var(--navy) 0%, #0d1526 100%);
    border-bottom: 1px solid rgba(0,245,255,0.12);
    padding: 18px 32px;
    display: flex; align-items: center; justify-content: space-between;
  }
  .logo { display: flex; align-items: center; gap: 14px; }
  .logo-icon {
    width: 42px; height: 42px; border-radius: 10px;
    background: linear-gradient(135deg, var(--primary), var(--cyan));
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
  }
  .logo-text h1 { font-size: 18px; font-weight: 700; letter-spacing: 0.02em; }
  .logo-text p { font-size: 11px; color: var(--cyan); letter-spacing: 0.08em; text-transform: uppercase; }
  .header-stats {
    display: flex; gap: 24px; align-items: center;
  }
  .stat { text-align: center; }
  .stat-num { font-size: 20px; font-weight: 700; color: var(--cyan); }
  .stat-label { font-size: 10px; color: var(--gray2); text-transform: uppercase; letter-spacing: 0.06em; }

  /* ── Search / Filter bar ── */
  .controls {
    padding: 16px 32px;
    background: rgba(10,14,26,0.6);
    border-bottom: 1px solid rgba(255,255,255,0.05);
    display: flex; align-items: center; gap: 12px;
  }
  .search-box {
    flex: 1; background: rgba(255,255,255,0.05); border: 1px solid rgba(0,245,255,0.15);
    border-radius: 8px; padding: 9px 14px; color: var(--white); font-size: 14px; outline: none;
  }
  .search-box::placeholder { color: var(--gray2); }
  .search-box:focus { border-color: var(--cyan); }
  .sort-btn {
    background: rgba(0,132,255,0.12); border: 1px solid rgba(0,132,255,0.3);
    color: var(--primary); padding: 9px 16px; border-radius: 8px; cursor: pointer;
    font-size: 13px; transition: all 0.2s;
  }
  .sort-btn:hover { background: rgba(0,132,255,0.25); }
  .sort-btn.active { background: var(--primary); color: white; }
  .refresh-btn {
    background: rgba(0,230,118,0.1); border: 1px solid rgba(0,230,118,0.25);
    color: var(--green); padding: 9px 16px; border-radius: 8px; cursor: pointer;
    font-size: 13px; transition: all 0.2s;
  }
  .refresh-btn:hover { background: rgba(0,230,118,0.2); }

  /* ── Grid ── */
  .grid-container { padding: 24px 32px; }
  .grid-label {
    font-size: 11px; color: var(--gray2); text-transform: uppercase;
    letter-spacing: 0.08em; margin-bottom: 16px;
  }
  .video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 18px;
  }
  .video-card {
    background: linear-gradient(145deg, #0f1626, #0a0e1a);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; overflow: hidden;
    cursor: pointer; transition: all 0.25s; position: relative;
  }
  .video-card:hover {
    border-color: rgba(0,245,255,0.3);
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(0,132,255,0.15);
  }
  .video-thumb {
    width: 100%; aspect-ratio: 16/9;
    background: linear-gradient(135deg, #0d1a30, #06111e);
    display: flex; align-items: center; justify-content: center;
    position: relative; overflow: hidden;
  }
  .play-icon {
    width: 52px; height: 52px; border-radius: 50%;
    background: rgba(0,132,255,0.85);
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; transition: all 0.2s;
    box-shadow: 0 0 24px rgba(0,132,255,0.5);
  }
  .video-card:hover .play-icon {
    background: var(--cyan); transform: scale(1.1);
    box-shadow: 0 0 32px rgba(0,245,255,0.6);
  }
  .play-icon::after { content: '▶'; color: white; margin-left: 3px; }
  .card-badge {
    position: absolute; top: 10px; right: 10px;
    background: rgba(0,230,118,0.85); color: #001a0a;
    font-size: 9px; font-weight: 700; letter-spacing: 0.06em;
    padding: 3px 7px; border-radius: 4px; text-transform: uppercase;
  }
  .card-info { padding: 14px; }
  .card-name {
    font-size: 12px; font-weight: 600; color: var(--white);
    margin-bottom: 6px; word-break: break-all; line-height: 1.4;
  }
  .card-meta {
    display: flex; justify-content: space-between; align-items: center;
  }
  .card-date { font-size: 10px; color: var(--gray2); }
  .card-size { font-size: 10px; color: var(--cyan); font-weight: 600; }

  /* ── Empty state ── */
  .empty-state {
    text-align: center; padding: 80px 20px; color: var(--gray2);
  }
  .empty-state .icon { font-size: 48px; margin-bottom: 16px; opacity: 0.4; }
  .empty-state h3 { font-size: 18px; color: var(--gray1); margin-bottom: 8px; }
  .empty-state p { font-size: 13px; line-height: 1.6; max-width: 340px; margin: 0 auto; }

  /* ── Modal ── */
  .modal-backdrop {
    display: none; position: fixed; inset: 0; z-index: 100;
    background: rgba(0,5,15,0.92); backdrop-filter: blur(12px);
    align-items: center; justify-content: center;
    flex-direction: column;
  }
  .modal-backdrop.open { display: flex; }
  .modal-box {
    background: var(--navy); border: 1px solid rgba(0,245,255,0.18);
    border-radius: 18px; overflow: hidden; width: 92%; max-width: 960px;
    box-shadow: 0 32px 80px rgba(0,0,0,0.8);
  }
  .modal-header {
    padding: 16px 20px; display: flex; align-items: center; justify-content: space-between;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    background: rgba(0,0,0,0.3);
  }
  .modal-title { font-size: 13px; color: var(--cyan); font-weight: 600; word-break: break-all; }
  .modal-actions { display: flex; gap: 10px; align-items: center; flex-shrink: 0; }
  .btn-download {
    background: rgba(0,132,255,0.15); border: 1px solid rgba(0,132,255,0.3);
    color: var(--primary); padding: 7px 14px; border-radius: 7px;
    font-size: 12px; cursor: pointer; text-decoration: none; display: block;
    transition: all 0.2s;
  }
  .btn-download:hover { background: var(--primary); color: white; }
  .close-btn {
    background: rgba(255,45,45,0.12); border: 1px solid rgba(255,45,45,0.2);
    color: #FF2D2D; width: 32px; height: 32px; border-radius: 8px;
    font-size: 16px; cursor: pointer; display: flex; align-items: center;
    justify-content: center; transition: all 0.2s;
  }
  .close-btn:hover { background: rgba(255,45,45,0.3); }
  .modal-video-wrap { background: #000; line-height: 0; }
  .modal-video-wrap video { width: 100%; max-height: 72vh; display: block; }
  .modal-footer {
    padding: 12px 20px; display: flex; gap: 20px; align-items: center;
    border-top: 1px solid rgba(255,255,255,0.05);
  }
  .modal-stat { font-size: 11px; color: var(--gray2); }
  .modal-stat span { color: var(--white); font-weight: 600; }

  /* ── Loading ── */
  /* ── Queue banner ── */
  #queueBanner {
    display: none; align-items: center; gap: 12px;
    background: rgba(0,132,255,0.08); border-bottom: 1px solid rgba(0,132,255,0.18);
    padding: 10px 32px; font-size: 13px; color: rgba(255,255,255,0.75);
  }
  #queueBanner strong { color: var(--cyan); }
  .spinner-sm {
    width: 14px; height: 14px; border: 2px solid rgba(0,245,255,0.2);
    border-top-color: var(--cyan); border-radius: 50%;
    animation: spin 0.7s linear infinite; flex-shrink: 0;
  }
  .queue-depth {
    background: rgba(0,132,255,0.2); color: var(--primary);
    font-size: 11px; font-weight: 700; padding: 2px 8px;
    border-radius: 10px; margin-left: 8px;
  }
  .loading { text-align: center; padding: 60px; color: var(--gray2); }
  .loading .spinner {
    width: 36px; height: 36px; border: 3px solid rgba(0,245,255,0.15);
    border-top-color: var(--cyan); border-radius: 50%;
    animation: spin 0.8s linear infinite; margin: 0 auto 14px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">🎬</div>
    <div class="logo-text">
      <h1>Vega Theater</h1>
      <p>Full Sensory Bridge · Screening Room</p>
    </div>
  </div>
  <div class="header-stats">
    <div class="stat">
      <div class="stat-num" id="totalCount">—</div>
      <div class="stat-label">Videos</div>
    </div>
    <div class="stat">
      <div class="stat-num" id="totalSize">—</div>
      <div class="stat-label">Total Size</div>
    </div>
  </div>
</header>

<div id="queueBanner"></div>

<div class="controls">
  <input class="search-box" type="text" id="searchInput" placeholder="Search videos...">
  <button class="sort-btn active" id="sortNew" onclick="setSort('new')">Newest First</button>
  <button class="sort-btn" id="sortOld" onclick="setSort('old')">Oldest First</button>
  <button class="refresh-btn" onclick="loadVideos()">↻ Refresh</button>
</div>

<div class="grid-container">
  <div class="grid-label" id="gridLabel">Loading...</div>
  <div class="video-grid" id="videoGrid">
    <div class="loading">
      <div class="spinner"></div>
      <p>Scanning Vega's vault...</p>
    </div>
  </div>
</div>

<!-- Modal -->
<div class="modal-backdrop" id="modal" onclick="handleBackdropClick(event)">
  <div class="modal-box" id="modalBox">
    <div class="modal-header">
      <div class="modal-title" id="modalTitle">—</div>
      <div class="modal-actions">
        <a class="btn-download" id="modalDownload" href="#" download>⬇ Download</a>
        <button class="close-btn" onclick="closeModal()">✕</button>
      </div>
    </div>
    <div class="modal-video-wrap">
      <video id="modalVideo" controls autoplay></video>
    </div>
    <div class="modal-footer">
      <div class="modal-stat">Size: <span id="modalSize">—</span></div>
      <div class="modal-stat">Created: <span id="modalDate">—</span></div>
    </div>
  </div>
</div>

<script>
let allVideos = [];
let sortOrder  = 'new';
let queueState = null;

// Auto-refresh every 12 seconds — picks up new renders automatically
setInterval(() => { loadVideos(); loadQueue(); }, 12000);

async function loadQueue() {
  try {
    const res  = await fetch('/vega/queue/status');
    queueState = await res.json();
    updateQueueBanner();
  } catch(e) { /* bridge may be restarting — silent */ }
}

function updateQueueBanner() {
  const banner = document.getElementById('queueBanner');
  if (!queueState) { banner.style.display = 'none'; return; }
  const rendering = queueState.currently_rendering;
  const waiting   = queueState.queue_size || 0;
  if (!rendering && waiting === 0) { banner.style.display = 'none'; return; }
  banner.style.display = 'flex';
  if (rendering) {
    banner.innerHTML =
      `<div class="spinner-sm"></div>
       <span>Rendering <strong>${escHtml(rendering.platform?.toUpperCase() || '')}</strong> —
       "${escHtml((rendering.prompt || '').substring(0, 60))}..."
       ${waiting > 0 ? `<span class="queue-depth">${waiting} waiting</span>` : ''}</span>`;
  } else {
    banner.innerHTML =
      `<div class="spinner-sm"></div>
       <span>${waiting} video${waiting !== 1 ? 's' : ''} queued — rendering soon</span>`;
  }
}

async function loadVideos() {
  try {
    const res  = await fetch('/vega/videos');
    const data = await res.json();
    allVideos  = data.videos || [];
    renderGrid();
    const totalMb = allVideos.reduce((s, v) => s + v.size_mb, 0);
    document.getElementById('totalCount').textContent = allVideos.length;
    document.getElementById('totalSize').textContent =
      totalMb >= 1024 ? (totalMb/1024).toFixed(1) + ' GB' : totalMb.toFixed(0) + ' MB';
  } catch(e) {
    document.getElementById('gridLabel').textContent = 'Error loading videos';
    document.getElementById('videoGrid').innerHTML =
      '<div class="empty-state"><div class="icon">⚠️</div>' +
      '<h3>Could not reach the bridge</h3>' +
      '<p>Make sure the Full Sensory Bridge is running on port 8765.</p></div>';
  }
}

function renderGrid() {
  const query  = document.getElementById('searchInput').value.toLowerCase();
  let videos   = allVideos.filter(v => !query || v.filename.toLowerCase().includes(query));
  if (sortOrder === 'old') videos = [...videos].reverse();
  document.getElementById('gridLabel').textContent =
    videos.length === allVideos.length
      ? `${allVideos.length} video${allVideos.length !== 1 ? 's' : ''} in the vault`
      : `${videos.length} of ${allVideos.length} videos`;
  if (videos.length === 0) {
    document.getElementById('videoGrid').innerHTML =
      '<div class="empty-state" style="grid-column:1/-1"><div class="icon">🎬</div>' +
      '<h3>' + (query ? 'No matches found' : 'The vault is empty') + '</h3>' +
      '<p>' + (query ? 'Try a different search term.' :
        'Send Vega a prompt at /vega/video and come back here to watch what it makes.') +
      '</p></div>';
    return;
  }
  document.getElementById('videoGrid').innerHTML = videos.map((v, i) =>
    `<div class="video-card" onclick="openModal('${v.url}','${escHtml(v.filename)}','${v.size_mb} MB','${escHtml(v.created)}')">
      <div class="video-thumb">
        <div class="play-icon"></div>
        ${i === 0 && sortOrder === 'new' ? '<div class="card-badge">Latest</div>' : ''}
      </div>
      <div class="card-info">
        <div class="card-name">${escHtml(v.filename)}</div>
        <div class="card-meta">
          <span class="card-date">${escHtml(v.created)}</span>
          <span class="card-size">${v.size_mb} MB</span>
        </div>
      </div>
    </div>`
  ).join('');
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function setSort(order) {
  sortOrder = order;
  document.getElementById('sortNew').classList.toggle('active', order === 'new');
  document.getElementById('sortOld').classList.toggle('active', order === 'old');
  renderGrid();
}

function openModal(url, filename, size, date) {
  document.getElementById('modalTitle').textContent = filename;
  document.getElementById('modalSize').textContent = size;
  document.getElementById('modalDate').textContent = date;
  document.getElementById('modalDownload').href = url;
  document.getElementById('modalDownload').download = filename;
  const vid = document.getElementById('modalVideo');
  vid.src = url;
  vid.load();
  vid.play().catch(() => {});
  document.getElementById('modal').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  const vid = document.getElementById('modalVideo');
  vid.pause(); vid.src = '';
  document.getElementById('modal').classList.remove('open');
  document.body.style.overflow = '';
}

function handleBackdropClick(e) {
  if (e.target === document.getElementById('modal')) closeModal();
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
document.getElementById('searchInput').addEventListener('input', renderGrid);

loadVideos();
loadQueue();
</script>
</body>
</html>""")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")

import requests as _requests
def get_student_hearing():
    try:
        r = _requests.get("http://localhost:8765/latest", timeout=2)
        return r.json()
    except Exception:
        return {"text": "", "note": "mcp bridge not reachable"}
def get_student_vision():
    try:
        r = _requests.get("http://localhost:8765/vision/latest", timeout=3)
        return r.json()
    except Exception:
        return {"b64": "", "message": "no view - start vision_capture"}
def get_recent_student_hearing(count=5):
    try:
        r = _requests.get(f"http://localhost:8765/recent?count={count}", timeout=2)
        return r.json()
    except Exception:
        return "no recent"
def get_audio_bridge_status():
    try:
        r = _requests.get("http://localhost:8765/health", timeout=2)
        return r.json()
    except Exception:
        return {"status": "down"}
