"""Reference swings and comparison against them."""
import logging
import mimetypes

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_settings_dep
from app.config import Settings
from app.models.database import Swing, SwingAnalysis, SwingStatus
from app.services.comparison import compute_comparison, rotation_note
from app.services.reference_library import ReferenceLibrary, ReferenceNotFound

logger = logging.getLogger(__name__)
router = APIRouter(tags=["references"])


def get_library(settings: Settings = Depends(get_settings_dep)) -> ReferenceLibrary:
    return ReferenceLibrary(settings)


@router.get("/references")
def list_references(library: ReferenceLibrary = Depends(get_library)) -> list[dict]:
    return library.list()


@router.get("/references/{ref_id}")
def get_reference(ref_id: str, library: ReferenceLibrary = Depends(get_library)) -> dict:
    try:
        profile = library.profile(ref_id)
    except ReferenceNotFound:
        raise HTTPException(404, "reference not found") from None
    return {**profile, "metrics": library.metrics(ref_id),
            "phases": library.phases(ref_id)["segments"]}


@router.get("/references/{ref_id}/keypoints")
def get_reference_keypoints(
    ref_id: str, library: ReferenceLibrary = Depends(get_library)
) -> dict:
    """Smoothed COCO-17 series — the one the reference's metrics came from."""
    try:
        return library.load(ref_id, "keypoints")
    except ReferenceNotFound:
        raise HTTPException(404, "reference keypoints not available") from None


@router.get("/references/{ref_id}/video/{artifact}")
def get_reference_artifact(
    ref_id: str, artifact: str, library: ReferenceLibrary = Depends(get_library)
) -> FileResponse:
    if artifact not in ("source", "thumbnail"):
        raise HTTPException(404, "unknown reference artifact")
    try:
        path = library.file_path(ref_id, artifact)
    except ReferenceNotFound:
        raise HTTPException(404, "reference not found") from None
    if not path.exists():
        raise HTTPException(404, f"{artifact} not available for this reference")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/swings/{swing_id}/compare/{ref_id}")
def compare_swing(
    swing_id: str,
    ref_id: str,
    db: Session = Depends(get_db),
    library: ReferenceLibrary = Depends(get_library),
) -> dict:
    swing = db.get(Swing, swing_id)
    if swing is None:
        raise HTTPException(404, "swing not found")
    if swing.status != SwingStatus.COMPLETED:
        raise HTTPException(409, "this swing has not finished processing")

    analysis = db.get(SwingAnalysis, swing_id)
    if analysis is None or not analysis.metrics:
        raise HTTPException(409, "this swing has no metrics to compare")

    if not library.exists(ref_id):
        raise HTTPException(404, "reference not found")

    reference_metrics = library.metrics(ref_id)
    result = compute_comparison(analysis.metrics, reference_metrics)
    return {
        "reference": library.profile(ref_id),
        "rotation_note": rotation_note(result["camera"]["user_view"]),
        **result,
    }
