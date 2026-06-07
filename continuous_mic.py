import asyncio
import base64
import json
import queue
import threading
from websockets.asyncio.client import connect as ws_connect
import sounddevice as sd
import numpy as np

audio_queue: queue.Queue = queue.Queue(maxsize=20)

async def sender(ws):
    """Background task that sends audio from the queue"""
    while True:
        try:
            payload = audio_queue.get_nowait()
            await ws.send(json.dumps(payload))
        except queue.Empty:
            await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Send error: {e}")
            break

async def continuous_stream():
    async with ws_connect("ws://localhost:8765/ws/audio") as ws:
        print("🎙️ Always-on microphone connected - Speak naturally")
        
        # Start sender task
        sender_task = asyncio.create_task(sender(ws))
        
        def audio_callback(indata, frames, time, status):
            if status:
                print("Audio status:", status)
            try:
                payload = {
                    "type": "audio",
                    "audio": base64.b64encode(indata.tobytes()).decode("utf-8"),
                    "sample_rate": 16000
                }
                audio_queue.put_nowait(payload)
            except queue.Full:
                pass  # drop old chunks if overwhelmed
        
        # Start microphone
        stream = sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype='int16',
            blocksize=8192,
            callback=audio_callback
        )
        stream.start()
        
        print("Listening live... (Ctrl+C to stop)")
        
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
