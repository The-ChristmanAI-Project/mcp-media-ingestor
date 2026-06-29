#!/usr/bin/env python3
"""
brockston_bridge_client.py — Connects Brockston to the Christman Full Sensory Bridge
via the /ws/brockston WebSocket endpoint. Forwards messages between Brockston and the bridge.
"""
import asyncio
import json
import logging
import os
import sys

import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [brockston_bridge] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

WS_URL = os.getenv("BROCKSTON_BRIDGE_WS", "ws://localhost:8765/ws/brockston")
SESSION_ID = os.getenv("BROCKSTON_SESSION_ID", "brockston_session")


async def connect_brockston_to_bridge():
    """Connect to the bridge and maintain the WebSocket connection."""
    while True:
        try:
            logger.info(f"Connecting to bridge at {WS_URL} ...")
            async with websockets.connect(WS_URL) as ws:
                logger.info("Connected — Brockston bridge link active.")

                await ws.send(json.dumps({
                    "type": "message",
                    "text": "Brockston connected to Christman Bridge",
                    "session_id": SESSION_ID
                }))

                async def heartbeat():
                    while True:
                        await asyncio.sleep(30)
                        try:
                            await ws.send(json.dumps({"type": "heartbeat"}))
                        except Exception:
                            break

                hb_task = asyncio.create_task(heartbeat())

                async for message in ws:
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")

                        if msg_type == "handshake":
                            logger.info(f"Bridge handshake: {data.get('message')}")
                        elif msg_type == "heartbeat_ack":
                            pass
                        elif msg_type == "message":
                            text = data.get("text", "")
                            logger.info(f"[Bridge → Brockston] {text}")
                        else:
                            logger.debug(f"Received: {data}")

                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON: {message}")

                hb_task.cancel()

        except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            logger.warning(f"Bridge connection lost ({e}). Retrying in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Unexpected error: {e}. Retrying in 10s...")
            await asyncio.sleep(10)


async def main():
    logger.info("Starting Brockston ↔ Bridge WebSocket client")
    await connect_brockston_to_bridge()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Brockston bridge client stopped.")
        sys.exit(0)