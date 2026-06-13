import asyncio
import base64
import json
from collections import deque
import numpy as np
from websockets.asyncio.client import connect as ws_connect
import sounddevice as sd

# Maonocaster E2 — Everett's production mic, native 16kHz
DEVICE_INDEX = 4
SAMPLE_RATE  = 16000

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
    async with ws_connect("ws://localhost:8765/ws/audio") as ws:
        print("🎙️ Maonocaster E2 — 16kHz native — ACTIVE")
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
