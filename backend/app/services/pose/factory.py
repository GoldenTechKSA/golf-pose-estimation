"""Pose backend selection with graceful model fallback."""
import logging

from app.config import Settings
from app.services.pose.base import PoseEstimator

logger = logging.getLogger(__name__)


def create_pose_estimator(settings: Settings) -> PoseEstimator:
    """Load the configured pose model, falling back down the configured list.

    The primary is yolo26m-pose; if the installed ultralytics can't resolve
    those weights yet, we fall back to yolo11m-pose (stable) rather than
    failing the job. The model that actually loaded is recorded on the
    estimator and stored with each swing's results.
    """
    from app.services.pose.yolo import YoloPoseEstimator  # lazy ML import

    candidates = [settings.pose_model, *settings.pose_model_fallbacks]
    errors: list[str] = []
    for name in candidates:
        try:
            estimator = YoloPoseEstimator(
                model_name=name,
                device=settings.pose_device,
                conf_threshold=settings.pose_conf_threshold,
            )
            if name != settings.pose_model:
                logger.warning("pose model %r unavailable, using fallback %r", settings.pose_model, name)
            return estimator
        except Exception as exc:  # noqa: BLE001 — collect and report all failures
            errors.append(f"{name}: {exc}")
            logger.warning("failed to load pose model %r: %s", name, exc)

    raise RuntimeError("no pose model could be loaded:\n" + "\n".join(errors))
