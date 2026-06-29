"""
Per-being HTTP bridge routers for TCAP family members.

Mounts at /{being}/send, /{being}/outbox/latest, /{being}/ping
Expected by christman_bridge_client.py in each being's repo.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Deque

from fastapi import APIRouter

BEINGS = ("alphavox", "inferno", "sierra", "brockston", "alphawolf")

_outboxes: dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=50))
_connected: dict[str, bool] = defaultdict(bool)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_outbox(being: str) -> dict:
    return {
        "from": being,
        "text": "queue empty",
        "timestamp": "",
    }


def make_being_router(being: str) -> APIRouter:
    router = APIRouter(prefix=f"/{being}", tags=[being])

    @router.post("/send")
    async def send(payload: dict) -> dict:
        entry = {
            "from": payload.get("from") or being,
            "text": payload.get("text") or "",
            "timestamp": payload.get("timestamp") or _utc_now(),
            **{k: v for k, v in payload.items() if k not in ("from", "text", "timestamp")},
        }
        if entry["text"]:
            _outboxes[being].append(entry)
        return {"ok": True, "queued": bool(entry["text"])}

    @router.get("/outbox/latest")
    async def outbox_latest() -> dict:
        if _outboxes[being]:
            return _outboxes[being].popleft()
        return _empty_outbox(being)

    @router.post("/ping")
    async def ping(payload: dict | None = None) -> dict:
        _connected[being] = True
        return {
            "ok": True,
            "being": being,
            "connected": True,
            "timestamp": (payload or {}).get("timestamp") or _utc_now(),
        }

    @router.get("/status")
    async def status() -> dict:
        return {
            "being": being,
            "connected": _connected[being],
            "outbox_depth": len(_outboxes[being]),
        }

    return router


def get_being_status(being: str) -> dict:
    return {
        "being": being,
        "connected": _connected[being],
        "outbox_depth": len(_outboxes[being]),
    }


ALL_ROUTERS = [make_being_router(name) for name in BEINGS]