"""Live processing progress over WebSocket.

The browser connects to /ws/swings/{id}/progress right after uploading.
The handler sends the current state from the database immediately, then
streams updates published by the worker on Redis pub/sub. If Redis isn't
reachable (inline dev mode), it degrades to polling the database — the
client can't tell the difference.

The socket closes itself once the swing reaches a terminal state.
"""
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.database import Swing, SwingStatus
from app.services.progress import progress_channel, serialize_progress

logger = logging.getLogger(__name__)
router = APIRouter()

POLL_INTERVAL_S = 0.5
_TERMINAL = (SwingStatus.COMPLETED.value, SwingStatus.FAILED.value)


def _load_swing_json(session_factory, swing_id: str) -> tuple[str | None, str | None]:
    """(progress json, status) for a swing, or (None, None) if missing."""
    with session_factory() as session:
        swing = session.get(Swing, swing_id)
        if swing is None:
            return None, None
        return serialize_progress(swing), swing.status.value


@router.websocket("/ws/swings/{swing_id}/progress")
async def swing_progress(websocket: WebSocket, swing_id: str) -> None:
    await websocket.accept()
    session_factory = websocket.app.state.session_factory
    settings = websocket.app.state.settings

    snapshot, status = await asyncio.to_thread(_load_swing_json, session_factory, swing_id)
    if snapshot is None:
        await websocket.close(code=4404, reason="swing not found")
        return

    try:
        await websocket.send_text(snapshot)
        if status in _TERMINAL:
            await websocket.close()
            return

        subscriber = await _redis_subscriber(settings.redis_url, swing_id)
        if subscriber is not None:
            await _stream_from_redis(websocket, subscriber, session_factory, swing_id)
        else:
            await _stream_by_polling(websocket, session_factory, swing_id, snapshot)
        await websocket.close()
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 — a dropped progress socket must not crash the app
        logger.exception("progress websocket error for swing %s", swing_id)


async def _redis_subscriber(redis_url: str, swing_id: str):
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(redis_url)
        await client.ping()
        pubsub = client.pubsub()
        await pubsub.subscribe(progress_channel(swing_id))
        return pubsub
    except Exception:  # noqa: BLE001
        logger.info("redis unavailable for swing %s; falling back to DB polling", swing_id)
        return None


async def _stream_from_redis(websocket: WebSocket, pubsub, session_factory,
                             swing_id: str) -> None:
    import json

    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=2.0)
            if msg is None:
                # Quiet channel — reconcile with the DB in case we subscribed
                # after the final publish (worker finished in the gap).
                snapshot, status = await asyncio.to_thread(
                    _load_swing_json, session_factory, swing_id)
                if status in _TERMINAL and snapshot:
                    await websocket.send_text(snapshot)
                    return
                continue
            data = msg["data"]
            text = data.decode() if isinstance(data, (bytes, bytearray)) else str(data)
            await websocket.send_text(text)
            if json.loads(text).get("status") in _TERMINAL:
                return
    finally:
        try:
            await pubsub.close()
        except Exception:  # noqa: BLE001
            pass


async def _stream_by_polling(websocket: WebSocket, session_factory, swing_id: str,
                             last_sent: str) -> None:
    while True:
        await asyncio.sleep(POLL_INTERVAL_S)
        snapshot, status = await asyncio.to_thread(_load_swing_json, session_factory, swing_id)
        if snapshot is None:
            return
        if snapshot != last_sent:
            await websocket.send_text(snapshot)
            last_sent = snapshot
        if status in _TERMINAL:
            return
