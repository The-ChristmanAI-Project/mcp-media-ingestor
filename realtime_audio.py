import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel
import numpy as np

logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Real-Time Audio Bridge")

# Shared buffer for latest transcript
latest_transcript: dict = {"text": "", "start": 0.0, "end": 0.0, "language": "", "updated": False}

# Load model once (small + int8 = fast on your Intel mac)
model = WhisperModel("small", device="cpu", compute_type="int8")

class AudioStreamProcessor:
    def __init__(self):
        self.buffer = bytearray()
        self.sample_rate = 16000
        self.chunk_duration = 2.0  # seconds per transcription chunk

    async def process_audio_chunk(self, audio_data: bytes, sample_rate: int = 16000) -> AsyncGenerator[dict, None]:
        """Process incoming audio bytes and yield transcripts in real time."""
        self.buffer.extend(audio_data)
        
        # Convert to float32 numpy for Whisper
        audio_np = np.frombuffer(self.buffer, dtype=np.int16).astype(np.float32) / 32768.0
        
        if len(audio_np) / sample_rate < self.chunk_duration:
            return  # Not enough audio yet
        
        # Transcribe the current buffer
        segments, info = model.transcribe(
            audio_np,
            beam_size=5,
            vad_filter=True,
            word_timestamps=True,
            language=None
        )
        
        full_text = []
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
            full_text.append(segment.text.strip())
        
        # Keep only recent audio in buffer (sliding window)
        keep_samples = int(self.sample_rate * 1.0)  # keep last 1s
        self.buffer = self.buffer[-keep_samples * 2:]  # 2 bytes per sample (int16)

@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    """Main WebSocket for real-time audio → transcription."""
    await websocket.accept()
    processor = AudioStreamProcessor()
    logger.info("Agent connected - live audio bridge open")
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "audio":
                # Expect base64 encoded PCM16 audio
                audio_b64 = data.get("audio")
                sample_rate = data.get("sample_rate", 16000)
                
                audio_bytes = base64.b64decode(audio_b64)
                
                async for transcript in processor.process_audio_chunk(audio_bytes, sample_rate):
                    await websocket.send_json(transcript)
                    # Update shared latest buffer
                    latest_transcript.update({
                        "text": transcript.get("text", ""),
                        "start": transcript.get("start", 0.0),
                        "end": transcript.get("end", 0.0),
                        "language": transcript.get("language", ""),
                        "updated": True
                    })
                    
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        logger.info("Agent disconnected from audio bridge")
    except Exception as e:
        logger.error(f"Audio WebSocket error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})

@app.get("/latest")
async def get_latest():
    """Return the most recent transcript segment for Claude to read."""
    if not latest_transcript["updated"]:
        return {"text": "", "message": "No transcript yet — speak into the mic."}
    return latest_transcript


# For testing / integration with MCP
@app.get("/health")
async def health():
    return {"status": "alive", "audio_bridge": "ready", "model": "faster-whisper-small"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
