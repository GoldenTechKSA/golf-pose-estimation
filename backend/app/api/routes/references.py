"""Reference swings and comparison against them."""
import logging
import mimetypes

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_settings_dep, get_storage_dep
from app.config import Settings
from app.core.keypoints import SKELETON_EDGES, KeypointSeries
from app.models.database import Swing, SwingAnalysis, SwingStatus
from app.services.comparison import compute_comparison, rotation_note
from app.services.overlay import build_overlay
from app.services.reference_library import ReferenceLibrary, ReferenceNotFound
from app.services.storage import LocalStorage

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


@router.get("/swings/{swing_id}/compare/{ref_id}/overlay")
def compare_overlay(
    swing_id: str,
    ref_id: str,
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage_dep),
    library: ReferenceLibrary = Depends(get_library),
) -> dict:
    """Time warp + spatial transform for drawing the reference over this swing."""
    swing = db.get(Swing, swing_id)
    if swing is None:
        raise HTTPException(404, "swing not found")
    analysis = db.get(SwingAnalysis, swing_id)
    if analysis is None or not analysis.metrics:
        raise HTTPException(409, "this swing has no analysis to align against")
    if not storage.artifact_exists(swing_id, "keypoints"):
        raise HTTPException(409, "this swing has no keypoints")
    if not library.exists(ref_id):
        raise HTTPException(404, "reference not found")

    user_events = analysis.metrics.get("events") or {}
    ref_events = library.phases(ref_id).get("events") or {}
    if not _has_anchors(user_events) or not _has_anchors(ref_events):
        raise HTTPException(409, "one of these swings is missing swing-phase anchors")

    user = KeypointSeries.from_json_payload(storage.load_json(swing_id, "keypoints"))
    reference = KeypointSeries.from_json_payload(library.load(ref_id, "keypoints"))

    profile = library.profile(ref_id)
    mirror = (profile.get("handedness") or "right") != (swing.handedness or "right")

    payload = build_overlay(user, user_events, reference, ref_events, mirror)
    payload["edges"] = [[int(a), int(b)] for edges in SKELETON_EDGES.values()
                        for a, b in edges]
    payload["reference_name"] = profile["display_name"]
    return payload


def _has_anchors(events: dict) -> bool:
    return all(k in events for k in ("takeaway", "top", "impact", "finish"))


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
    profile = library.profile(ref_id)
    result = compute_comparison(analysis.metrics, reference_metrics)
    return {
        "reference": profile,
        "rotation_note": rotation_note(result["camera"]["user_view"]),
        "pipeline_note": _pipeline_note(profile, swing),
        **result,
    }


def _pipeline_note(profile: dict, swing: Swing) -> str | None:
    """Two swings run through different pose settings differ by the settings.

    Inference resolution moves these metrics by more than the golfer differences
    a comparison exists to show, so a mismatch is a caveat on every row, not a
    footnote. Both sides are compared at the values recorded when each was
    processed — never the live settings, which may have changed since.
    """
    ref_imgsz = profile.get("pose_imgsz")
    ref_model = profile.get("pose_model")
    if ref_imgsz is None:
        return ("This reference was built before the pipeline settings were "
                "recorded, so we cannot tell whether it matches your swing.")

    mismatches = []
    if swing.pose_imgsz is not None and ref_imgsz != swing.pose_imgsz:
        mismatches.append(f"inference resolution ({ref_imgsz} vs {swing.pose_imgsz})")
    if ref_model and swing.pose_model and ref_model != swing.pose_model:
        mismatches.append(f"pose model ({ref_model} vs {swing.pose_model})")
    if not mismatches:
        return None
    return ("Your swing and this reference were measured with a different "
            + " and ".join(mismatches)
            + ". Changing those settings moves these metrics on its own, so part "
              "of every gap below is the pipeline rather than the golfer.")
