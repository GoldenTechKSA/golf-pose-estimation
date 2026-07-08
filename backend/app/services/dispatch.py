"""Hand a swing off for processing, per the configured mode.

celery: enqueue to the worker via Redis (production / docker-compose).
inline: process in a daemon thread of the API process — lets the whole
        backend run as a single process (no Redis/worker) for quick local
        dev and integration tests. The WebSocket falls back to DB polling
        in this mode.
"""
import logging
import threading

from app.config import Settings

logger = logging.getLogger(__name__)


def enqueue_processing(settings: Settings, swing_id: str) -> None:
    if settings.processing_mode == "inline":
        from app.services.pipeline import run_swing_processing

        thread = threading.Thread(
            target=run_swing_processing, args=(swing_id, settings),
            name=f"swing-{swing_id[:8]}", daemon=True,
        )
        thread.start()
        logger.info("processing swing %s inline", swing_id)
    else:
        from app.tasks.process_swing import process_swing  # lazy: celery import

        process_swing.delay(swing_id)
        logger.info("enqueued swing %s to celery", swing_id)
