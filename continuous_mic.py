import asyncio
import base64
import json
from collections import deque
import numpy as np
from websockets.asyncio.client import connect as ws_connect
import sounddevice as sd

# Auto-detect available input device or use env override
import os
DEFAULT_DEVICE = int(os.getenv("CHRISTMAN_MIC_DEVICE", "5"))  # iMac Microphone = 5
SAMPLE_RATE  = 16000

def find_input_device():
    """Find the first available input device, preferring the default."""
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0 and i == DEFAULT_DEVICE:
            return i
    # Fallback to first available
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            return i
    raise RuntimeError("No input devices available")

DEVICE_INDEX = find_input_device()

audio_queue: deque = deque(maxlen=50)


async def sender(ws):
    while True:
        try:
            if audio_queue:
                payload = audio_queue.popleft()
                await ws.send(json.dumps(payload))
            else:
                await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Send error: {e}")
            break


async def continuous_stream():
    # List available input devices on startup
    print("🎙️ Available input devices:")
    for i, d in enumerate(sd.query_devices()):
        if d['max_input_channels'] > 0:
            marker = " ← USING" if i == DEVICE_INDEX else ""
            print(f"  [{i}] {d['name']} — {d['max_input_channels']} ch, {d['default_samplerate']:.0f} Hz{marker}")
    
    async with ws_connect("ws://localhost:8765/ws/audio") as ws:
        print(f"🎙️ Device {DEVICE_INDEX} @ 16kHz — ACTIVE")
        sender_task = asyncio.create_task(sender(ws))

        def audio_callback(indata, frames, time, status):
            if status:
                print("Audio status:", status)
            payload = {
                "type": "audio",
                "audio": base64.b64encode(indata.tobytes()).decode("utf-8"),
                "sample_rate": SAMPLE_RATE
            }
            audio_queue.append(payload)

        stream = sd.InputStream(
            device=DEVICE_INDEX,
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='int16',
            blocksize=8192,
            callback=audio_callback
        )
        stream.start()
        print("Listening on Maonocaster E2 at 16kHz — no resampling. Speak!")

        try:
            while True:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        finally:
            stream.stop()
            stream.close()
            sender_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(continuous_stream())
    except KeyboardInterrupt:
        print("\n🛑 Stopped.")
    except Exception as e:
        print(f"Error: {e}")
