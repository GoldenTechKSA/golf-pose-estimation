"""End-to-end swing processing pipeline.

This is the composition root for a processing job: it wires storage, the
pose backend, and progress reporting together and walks one swing through

    normalize video -> extract keypoints -> render annotated video

reporting progress as it goes. It runs identically inside a Celery worker
(production) or a background thread of the API process (inline dev mode) —
the only difference is who calls `process()`.

Progress is mapped onto a single 0-100 scale across stages so the frontend
can show one continuous bar.
"""
import logging
from typing import Callable

from sqlalchemy.orm import sessionmaker

from app.config import Settings, get_settings
from app.core.smoothing import smooth_series
from app.models.database import ProcessingStage, Swing, create_session_factory
from app.services import video_processor as vp
from app.services.pose import PoseEstimator, create_pose_estimator
from app.services.progress import ProgressReporter
from app.services.storage import LocalStorage, get_storage

logger = logging.getLogger(__name__)

# Stage boundaries on the unified progress bar.
_PREPARE_SPAN = (0.0, 10.0)
_EXTRACT_SPAN = (10.0, 62.0)
_RENDER_SPAN = (62.0, 97.0)


def _span_progress(span: tuple[float, float], fraction: float) -> float:
    lo, hi = span
    return lo + (hi - lo) * min(1.0, max(0.0, fraction))


class SwingProcessor:
    def __init__(self, settings: Settings, session_factory: sessionmaker,
                 storage: LocalStorage,
                 estimator_factory: Callable[[], PoseEstimator] | None = None):
        self.settings = settings
        self.session_factory = session_factory
        self.storage = storage
        self._estimator_factory = estimator_factory or (lambda: _cached_estimator(settings))

    def process(self, swing_id: str) -> None:
        reporter = ProgressReporter(swing_id, self.session_factory, self.settings.redis_url)
        try:
            self._run(swing_id, reporter)
            reporter.complete()
        except Exception as exc:  # noqa: BLE001 — job boundary: record any failure
            logger.exception("processing failed for swing %s", swing_id)
            reporter.fail(str(exc))

    def _run(self, swing_id: str, reporter: ProgressReporter) -> None:
        original = self.storage.original_path(swing_id)
        if original is None:
            raise FileNotFoundError(f"no uploaded video found for swing {swing_id}")

        # 1. Normalize the upload and capture a poster frame.
        reporter.update(ProcessingStage.PREPARING, _span_progress(_PREPARE_SPAN, 0.1),
                        "normalizing video")
        source = self.storage.artifact_path(swing_id, "source")
        vp.normalize_video(original, source, self.settings.max_processing_dim)
        info = vp.probe(source)
        vp.save_thumbnail(source, self.storage.artifact_path(swing_id, "thumbnail"))
        self._update_swing(swing_id, fps=info.fps, width=info.width, height=info.height,
                           n_frames=info.n_frames, duration=info.duration)
        reporter.update(ProcessingStage.PREPARING, _span_progress(_PREPARE_SPAN, 1.0),
                        "video ready")

        # 2. Pose estimation over every frame.
        estimator = self._estimator_factory()
        raw = vp.extract_keypoints(
            source, estimator,
            on_progress=lambda f, m: reporter.update(
                ProcessingStage.EXTRACTING_KEYPOINTS, _span_progress(_EXTRACT_SPAN, f), m),
        )
        self.storage.save_json(swing_id, "keypoints", raw.to_json_payload())
        self._update_swing(swing_id, pose_model=estimator.model_name)

        # 3. Clean the tracks and render the annotated video.
        smoothed = smooth_series(raw, conf_threshold=self.settings.pose_conf_threshold)
        vp.render_annotated(
            source, self.storage.artifact_path(swing_id, "annotated"), smoothed,
            on_progress=lambda f, m: reporter.update(
                ProcessingStage.RENDERING, _span_progress(_RENDER_SPAN, f), m),
        )

    def _update_swing(self, swing_id: str, **fields) -> None:
        with self.session_factory() as session:
            swing = session.get(Swing, swing_id)
            if swing is None:
                raise LookupError(f"swing {swing_id} disappeared from the database")
            for key, value in fields.items():
                setattr(swing, key, value)
            session.commit()


_estimator_singleton: PoseEstimator | None = None


def _cached_estimator(settings: Settings) -> PoseEstimator:
    """Load the pose model once per process — it's by far the slowest init."""
    global _estimator_singleton
    if _estimator_singleton is None:
        _estimator_singleton = create_pose_estimator(settings)
    return _estimator_singleton


def build_processor(settings: Settings | None = None) -> SwingProcessor:
    """Standalone composition root (Celery worker / inline thread entrypoint)."""
    settings = settings or get_settings()
    return SwingProcessor(
        settings=settings,
        session_factory=create_session_factory(settings),
        storage=get_storage(settings),
    )


def run_swing_processing(swing_id: str, settings: Settings | None = None) -> None:
    build_processor(settings).process(swing_id)
