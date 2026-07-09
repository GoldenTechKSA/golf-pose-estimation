"""End-to-end swing processing pipeline.

This is the composition root for a processing job: it wires storage, the
pose backend, and progress reporting together and walks one swing through

    normalize video -> extract keypoints -> detect phases + compute metrics
    -> render annotated video -> generate coaching feedback

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
from app.core.timing import format_timings, record
from app.models.database import ProcessingStage, Swing, SwingAnalysis, create_session_factory
from app.services import video_processor as vp
from app.services.coaching import generate_coaching
from app.services.metric_calculator import compute_metrics
from app.services.phase_detector import PHASE_COLORS_BGR, detect_phases
from app.services.pose import PoseEstimator, create_pose_estimator
from app.services.progress import ProgressReporter
from app.services.storage import LocalStorage, get_storage

logger = logging.getLogger(__name__)

# Stage boundaries on the unified progress bar, weighted by measured wall-clock
# share rather than guessed. On the sample swing (yolo11n @ 640, CPU, 151
# frames, 14.4s total): prepare 7.5%, extract 77.6%, analyze <0.1%, render
# 14.9%. The old weights gave extract 47% and render 31%, so the bar sprinted to
# 55% and then sat still through the longest stage — which is most of what
# "analysis feels slow" actually was. Coaching keeps a wider slice than it will
# usually need because it is a network call with variable latency.
_PREPARE_SPAN = (0.0, 7.0)
_EXTRACT_SPAN = (7.0, 78.0)
_ANALYZE_SPAN = (78.0, 79.0)
_RENDER_SPAN = (79.0, 92.0)
_COACH_SPAN = (92.0, 99.0)


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
        handedness = self._swing_field(swing_id, "handedness") or self.settings.default_handedness
        timings: dict[str, float] = {}

        # 1. Normalize the upload and capture a poster frame.
        reporter.update(ProcessingStage.PREPARING, _span_progress(_PREPARE_SPAN, 0.1),
                        "normalizing video")
        source = self.storage.artifact_path(swing_id, "source")
        with record(timings, "prepare_s"):
            vp.normalize_video(original, source, self.settings.max_processing_dim)
            info = vp.probe(source)
            vp.save_thumbnail(source, self.storage.artifact_path(swing_id, "thumbnail"))
        self._update_swing(swing_id, fps=info.fps, width=info.width, height=info.height,
                           n_frames=info.n_frames, duration=info.duration)
        reporter.update(ProcessingStage.PREPARING, _span_progress(_PREPARE_SPAN, 1.0),
                        "video ready")

        # 2. Pose estimation over every frame.
        estimator = self._estimator_factory()
        with record(timings, "extract_s"):
            raw = vp.extract_keypoints(
                source, estimator,
                on_progress=lambda f, m: reporter.update(
                    ProcessingStage.EXTRACTING_KEYPOINTS, _span_progress(_EXTRACT_SPAN, f), m),
            )
        self.storage.save_json(swing_id, "keypoints", raw.to_json_payload())
        self._update_swing(swing_id, pose_model=estimator.model_name)

        # 3. Clean the tracks, segment the swing, and compute biomechanics.
        with record(timings, "analyze_s"):
            smoothed = smooth_series(raw, conf_threshold=self.settings.pose_conf_threshold)
            reporter.update(ProcessingStage.ANALYZING, _span_progress(_ANALYZE_SPAN, 0.2),
                            "detecting swing phases")
            phases = detect_phases(smoothed)
            reporter.update(ProcessingStage.ANALYZING, _span_progress(_ANALYZE_SPAN, 0.6),
                            "computing biomechanical metrics")
            metrics = compute_metrics(smoothed, phases, handedness)
        if phases.warnings:
            metrics["warnings"] = phases.warnings
        self._save_analysis(swing_id, phases=phases.segments, metrics=metrics)

        # 4. Render the annotated video, phase-colored.
        with record(timings, "render_s"):
            vp.render_annotated(
                source, self.storage.artifact_path(swing_id, "annotated"), smoothed,
                frame_labels=phases.frame_labels,
                label_colors=PHASE_COLORS_BGR,
                on_progress=lambda f, m: reporter.update(
                    ProcessingStage.RENDERING, _span_progress(_RENDER_SPAN, f), m),
            )

        # 5. AI coaching feedback (best-effort — never fails the job).
        reporter.update(ProcessingStage.COACHING, _span_progress(_COACH_SPAN, 0.2),
                        "generating coaching feedback")
        with record(timings, "coach_s"):
            coaching = generate_coaching(metrics, phases.segments, handedness, self.settings)
        if coaching is not None:
            self._save_analysis(swing_id, coaching=coaching)

        logger.info(
            "pipeline timings %s",
            format_timings(
                swing=swing_id,
                total_s=round(sum(timings.values()), 3),
                **timings,
                n_frames=info.n_frames,
                fps=round(info.fps, 2),
                dims=f"{info.width}x{info.height}",
                pose_model=estimator.model_name,
                pose_imgsz=self.settings.pose_imgsz,
            ),
        )

    def _swing_field(self, swing_id: str, field: str):
        with self.session_factory() as session:
            swing = session.get(Swing, swing_id)
            return getattr(swing, field, None) if swing else None

    def _save_analysis(self, swing_id: str, **fields) -> None:
        with self.session_factory() as session:
            analysis = session.get(SwingAnalysis, swing_id)
            if analysis is None:
                analysis = SwingAnalysis(swing_id=swing_id)
                session.add(analysis)
            for key, value in fields.items():
                setattr(analysis, key, value)
            session.commit()

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
