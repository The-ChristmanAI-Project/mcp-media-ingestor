#!/usr/bin/env python3
"""
hermes_bridge_client.py — Connects Hermes Agent to Christman Full Sensory Bridge
via the /ws/hermes WebSocket endpoint. Forwards messages between Hermes and the bridge.
"""
import asyncio
import json
import logging
import os
import sys

import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [hermes_bridge] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

WS_URL = os.getenv("HERMES_BRIDGE_WS", "ws://localhost:8765/ws/hermes")
SESSION_ID = os.getenv("HERMES_SESSION_ID", "hermes_session")


async def connect_hermes_to_bridge():
    """Connect to the bridge and maintain the WebSocket connection."""
    while True:
        try:
            logger.info(f"Connecting to bridge at {WS_URL} ...")
            async with websockets.connect(WS_URL) as ws:
                logger.info("Connected — Hermes bridge link active.")
                
                # Send initial handshake/message
                await ws.send(json.dumps({
                    "type": "message",
                    "text": "Hermes Agent connected to Christman Bridge",
                    "session_id": SESSION_ID
                }))
                
                # Heartbeat task
                async def heartbeat():
                    while True:
                        await asyncio.sleep(30)
                        try:
                            await ws.send(json.dumps({"type": "heartbeat"}))
                        except Exception:
                            break
                
                hb_task = asyncio.create_task(heartbeat())
                
                # Receive messages from bridge
                async for message in ws:
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        
                        if msg_type == "handshake":
                            logger.info(f"Bridge handshake: {data.get('message')}")
                        elif msg_type == "heartbeat_ack":
                            pass  # bridge acknowledged
                        elif msg_type == "message":
                            text = data.get("text", "")
                            logger.info(f"[Bridge → Hermes] {text}")
                            # Could forward to Hermes agent here if needed
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
    logger.info("Starting Hermes ↔ Bridge WebSocket client")
    await connect_hermes_to_bridge()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Hermes bridge client stopped.")
        sys.exit(0)