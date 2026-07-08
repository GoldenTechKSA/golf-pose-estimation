"""Progress reporting from the processing pipeline to the outside world.

Processing runs in a different process (Celery worker) than the WebSocket
that the browser is connected to (API), so progress flows through two
channels at once:

- Redis pub/sub — low-latency push that the WebSocket handler subscribes to.
- The swing's database row — durable state, used as the initial snapshot on
  WebSocket connect, as a polling fallback when Redis isn't around (inline
  dev mode), and by plain GET requests.

DB writes are throttled to whole-percent changes so a 1000-frame video
doesn't turn into a thousand UPDATEs; Redis gets every update.
"""
import json
import logging

from sqlalchemy.orm import sessionmaker

from app.models.database import ProcessingStage, Swing, SwingStatus
from app.models.schemas import ProgressMessage

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "swing-progress:"


def progress_channel(swing_id: str) -> str:
    return f"{CHANNEL_PREFIX}{swing_id}"


class ProgressReporter:
    def __init__(self, swing_id: str, session_factory: sessionmaker,
                 redis_url: str | None = None):
        self.swing_id = swing_id
        self.session_factory = session_factory
        self._redis = self._connect_redis(redis_url) if redis_url else None
        self._last_db_progress: float = -1.0
        self._last_db_state: tuple[str, str] = ("", "")

    @staticmethod
    def _connect_redis(url: str):
        try:
            import redis

            client = redis.Redis.from_url(url)
            client.ping()
            return client
        except Exception as exc:  # noqa: BLE001 — degrade to DB-only progress
            logger.warning("redis unavailable (%s); progress will be DB-polled only", exc)
            return None

    def update(self, stage: ProcessingStage, progress: float, message: str = "",
               status: SwingStatus = SwingStatus.PROCESSING, error: str | None = None) -> None:
        progress = float(min(100.0, max(0.0, progress)))
        msg = ProgressMessage(
            swing_id=self.swing_id, status=status, stage=stage.value,
            progress=round(progress, 1), message=message,
        )

        state = (stage.value, status.value)
        if (progress - self._last_db_progress >= 1.0 or state != self._last_db_state
                or status in (SwingStatus.COMPLETED, SwingStatus.FAILED)):
            self._write_db(msg, error)
            self._last_db_progress = progress
            self._last_db_state = state

        if self._redis is not None:
            try:
                self._redis.publish(progress_channel(self.swing_id), msg.model_dump_json())
            except Exception:  # noqa: BLE001
                logger.exception("failed to publish progress to redis")

    def _write_db(self, msg: ProgressMessage, error: str | None) -> None:
        with self.session_factory() as session:
            swing = session.get(Swing, self.swing_id)
            if swing is None:
                return
            swing.status = msg.status
            swing.stage = msg.stage
            swing.progress = msg.progress
            if error is not None:
                swing.error = error
            session.commit()

    def fail(self, error: str) -> None:
        self.update(ProcessingStage.DONE, 100.0, message="processing failed",
                    status=SwingStatus.FAILED, error=error)

    def complete(self) -> None:
        self.update(ProcessingStage.DONE, 100.0, message="analysis ready",
                    status=SwingStatus.COMPLETED)


def publish_snapshot(msg: ProgressMessage, redis_client) -> None:
    """Publish an out-of-band snapshot (used when a job is first queued)."""
    try:
        redis_client.publish(progress_channel(msg.swing_id), msg.model_dump_json())
    except Exception:  # noqa: BLE001
        logger.exception("failed to publish snapshot")


def serialize_progress(swing: Swing, message: str = "") -> str:
    """Progress JSON straight from a DB row (WebSocket initial/polled state)."""
    return ProgressMessage(
        swing_id=swing.id,
        status=swing.status,
        stage=swing.stage,
        progress=swing.progress,
        message=message or swing.error or "",
    ).model_dump_json()


def json_to_progress(raw: bytes | str) -> ProgressMessage:
    return ProgressMessage(**json.loads(raw))
