import asyncio
import base64
import json
import sys

import websockets

async def test_audio_ws(audio_file: str):
    async with websockets.connect("ws://localhost:8765/ws/audio") as ws:
        print(f"✅ Connected to real-time audio bridge")
        print(f"Sending: {audio_file}")
        
        # Read and encode audio
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()
        
        payload = {
            "type": "audio",
            "audio": base64.b64encode(audio_bytes).decode("utf-8"),
            "sample_rate": 16000
        }
        
        await ws.send(json.dumps(payload))
        print("Audio sent. Waiting for transcription...\n")
        
        # Receive transcripts
        try:
            async for message in ws:
                data = json.loads(message)
                if data.get("type") == "transcript":
                    print(f"[{data['start']:.2f}s → {data['end']:.2f}s] {data['text']}")
                else:
                    print("Received:", data)
        except Exception as e:
            print("Connection closed or error:", e)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_websocket.py <audio_file>")
        sys.exit(1)
    asyncio.run(test_audio_ws(sys.argv[1]))
