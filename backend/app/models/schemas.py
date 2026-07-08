"""Pydantic request/response models — the API contract with the frontend."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.database import ProcessingStage, Swing, SwingStatus


class UploadResponse(BaseModel):
    id: str
    status: SwingStatus


class PhaseSegment(BaseModel):
    """One detected swing phase as a frame/time span of the source video."""

    name: str
    start_frame: int
    end_frame: int  # inclusive
    start_time: float
    end_time: float


class ProgressMessage(BaseModel):
    """Payload pushed over the progress WebSocket (and Redis pub/sub)."""

    swing_id: str
    status: SwingStatus
    stage: str
    progress: float = Field(ge=0, le=100)
    message: str = ""


class VideoUrls(BaseModel):
    original: str
    annotated: str | None = None
    thumbnail: str | None = None


class SwingSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    original_filename: str
    handedness: str
    status: SwingStatus
    stage: str
    progress: float
    error: str | None = None
    duration: float | None = None
    fps: float | None = None
    pose_model: str | None = None


class SwingDetail(SwingSummary):
    width: int | None = None
    height: int | None = None
    n_frames: int | None = None
    video_urls: VideoUrls | None = None
    phases: list[PhaseSegment] | None = None
    metrics: dict | None = None
    coaching: dict | None = None


def swing_to_detail(swing: Swing, api_prefix: str) -> SwingDetail:
    """Assemble the full response for one swing row."""
    detail = SwingDetail.model_validate(swing)
    base = f"{api_prefix}/swings/{swing.id}"
    detail.video_urls = VideoUrls(
        original=f"{base}/video/original",
        annotated=f"{base}/video/annotated" if swing.status == SwingStatus.COMPLETED else None,
        thumbnail=f"{base}/video/thumbnail" if swing.stage not in (
            ProcessingStage.QUEUED.value, ProcessingStage.PREPARING.value
        ) else None,
    )
    if swing.analysis is not None:
        if swing.analysis.phases:
            detail.phases = [PhaseSegment(**p) for p in swing.analysis.phases]
        detail.metrics = swing.analysis.metrics
        detail.coaching = swing.analysis.coaching
    return detail
