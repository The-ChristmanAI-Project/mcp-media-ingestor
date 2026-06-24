import base64
import logging
import os
from datetime import datetime
from typing import AsyncGenerator, Dict

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from faster_whisper import WhisperModel
from fastmcp import FastMCP
from mcp.types import ImageContent

from _paths import ensure_family_paths
ensure_family_paths()

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

        segments, info = whisper_model.transcribe(
            audio_np, beam_size=5, vad_filter=True, language="en", word_timestamps=True
        )

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


def make_image_content_from_b64(b64: str, fmt: str = "JPEG") -> ImageContent:
    """Create ImageContent for live frames (mirrors server.py logic for total vision)."""
    # For live we assume client sends reasonable size; optionally decode+thumbnail here if needed.
    mime = "image/jpeg" if fmt.upper() == "JPEG" else f"image/{fmt.lower()}"
    return ImageContent(type="image", data=b64, mimeType=mime)


mcp = FastMCP("mcp-media-ingestor")
mcp_app = mcp.http_app(path="/mcp")

app = FastAPI(title="Christman Full Sensory Bridge", lifespan=mcp_app.lifespan)
app.mount("/mcp", mcp_app)


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
        active_connections["mic"] -= 1
    except Exception as e:
        logger.error(f"Audio WebSocket error: {e}")


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
        active_connections["vision"] -= 1
    except Exception as e:
        logger.error(f"Video WebSocket error: {e}")

# ── Yorkie Student WebSocket ──────────────────────────────────────────────────
yorkie_inbox: list[dict] = []
yorkie_outbox: list[dict] = []
active_connections["yorkie"] = 0

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


# ── Hermes Agent WebSocket ────────────────────────────────────────────────────
@app.websocket("/ws/hermes")
async def websocket_hermes(websocket: WebSocket):
    await websocket.accept()
    active_connections["hermes"] = active_connections.get("hermes", 0) + 1
    logger.info(f"🤖 HERMES CONNECTED — Total: {active_connections['hermes']}")

    await websocket.send_json({
        "type": "handshake",
        "message": "Christman Bridge ACTIVE. Hermes Agent connected.",
        "timestamp": datetime.now().isoformat()
    })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                entry = {
                    "from": "hermes_agent",
                    "text": data.get("text", ""),
                    "timestamp": datetime.now().isoformat(),
                    "session_id": data.get("session_id", "--")
                }
                hermes_outbox.append(entry)
                logger.info(f"[HERMES → BRIDGE] {entry['text']}")

            elif msg_type == "heartbeat":
                await websocket.send_json({"type": "heartbeat_ack", "timestamp": datetime.now().isoformat()})

    except WebSocketDisconnect:
        active_connections["hermes"] = max(0, active_connections.get("hermes", 1) - 1)
        logger.info(f"🤖 HERMES DISCONNECTED — Remaining: {active_connections.get('hermes', 0)}")
    except Exception as e:
        logger.error(f"Hermes WebSocket error: {e}")


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

@app.get("/latest")
async def get_latest_http():
    return latest_transcript

@app.get("/vision/latest")
async def get_latest_frame_http():
    if not latest_frame.get("b64"):
        return {"b64": "", "message": "No frame yet — connect a vision client."}
    return latest_frame

@app.get("/health")
async def health():
    return {
        "status": "alive",
        "bridge": "Christman Full Sensory",
        "mic_clients": active_connections["mic"],
        "vision_clients": active_connections["vision"],
        "hermes_clients": active_connections["hermes"],
        "riley_connected": active_connections["riley"] > 0,
        "reactive": True
    }


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
