import base64
import logging
from typing import AsyncGenerator, Dict

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel
from fastmcp import FastMCP

# === Your Christman Adapters ===
from _paths import ensure_family_paths
ensure_family_paths()

import EAR
import SPEAK
import TONE
# import PHONEMES, OCR, etc. as needed

logger = logging.getLogger(__name__)

whisper_model = WhisperModel("small", device="cpu", compute_type="int8")

active_connections: Dict[str, int] = {"mic": 0}
latest_transcript = {"text": "", "timestamp": 0}

class AudioStreamProcessor:
    def __init__(self):
        self.buffer = bytearray()
        self.sample_rate = 16000
        self.chunk_duration = 0.8

    async def process_audio_chunk(self, audio_data: bytes, sample_rate: int = 16000) -> AsyncGenerator[dict, None]:
        self.buffer.extend(audio_data)
        audio_np = np.frombuffer(self.buffer, dtype=np.int16).astype(np.float32) / 32768.0
        
        if len(audio_np) / sample_rate < 0.6:
            return
        
        segments, info = whisper_model.transcribe(
            audio_np, beam_size=5, vad_filter=True, word_timestamps=True, language=None
        )
        
        for segment in segments:
            transcript = {
                "type": "transcript",
                "text": segment.text.strip(),
                "start": segment.start,
                "end": segment.end,
                "language": info.language,
                "confidence": info.language_probability
            }
            yield transcript
            latest_transcript.update({"text": transcript["text"], "timestamp": transcript["end"]})
        
        keep_samples = int(self.sample_rate * 1.5)
        self.buffer = self.buffer[-keep_samples * 2:]

mcp = FastMCP("mcp-media-ingestor")
mcp_app = mcp.http_app(path="/mcp")

app = FastAPI(title="Christman Full Sensory Bridge", lifespan=mcp_app.lifespan)
app.mount("/mcp", mcp_app)

@app.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket):
    await websocket.accept()
    active_connections["mic"] += 1
    processor = AudioStreamProcessor()
    
    logger.info(f"🎙️ MIC CONNECTED — Total: {active_connections['mic']}")
    await websocket.send_json({"type": "status", "message": "Christman Live Bridge ACTIVE — All agents can hear you."})
    
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "audio":
                audio_b64 = data.get("audio")
                sample_rate = data.get("sample_rate", 16000)
                audio_bytes = base64.b64decode(audio_b64)
                
                async for transcript in processor.process_audio_chunk(audio_bytes, sample_rate):
                    await websocket.send_json(transcript)
    except WebSocketDisconnect:
        active_connections["mic"] -= 1
        logger.info(f"🎙️ MIC DISCONNECTED — Remaining: {active_connections['mic']}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

# === Your Real Christman Tools ===
@mcp.tool
async def describe_audio_bridge() -> str:
    return f"""
🔴 CHRISTMAN FULL SENSORY BRIDGE — LIVE

Microphones connected: {active_connections["mic"]}
Status: Always listening, fully reactive

Your voice reaches every agent in real time.
No clicks. Just you.

Call get_latest_transcript() after you speak.
"""

@mcp.tool
async def get_latest_transcript() -> str:
    text = latest_transcript.get("text", "")
    return text if text else "No speech detected yet. Speak — I'm listening."

@mcp.tool
async def speak_text(text: str, emotion: str = "neutral") -> str:
    """Speak using your real Christman Voice SDK."""
    result = SPEAK.speak(text=text, emotion=emotion)
    return f"Spoken with {result.get('engine')}: {result.get('status')}"

@mcp.tool
async def analyze_tone(audio_path: str) -> dict:
    """Analyze tone using your real TONE adapter."""
    return TONE.analyze_tone(audio_path)

@mcp.tool
async def capture_voice(duration: float = 6.0) -> str:
    """Capture live audio using your EAR."""
    path = EAR.listen(max_duration=duration)
    return f"Voice captured: {path}"

@app.get("/health")
async def health():
    return {
        "status": "alive",
        "bridge": "Christman Full Sensory",
        "mic_clients": active_connections["mic"],
        "reactive": True
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
