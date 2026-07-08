"""Swing endpoints: upload, list, detail, artifacts, delete."""
import logging
import mimetypes
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_settings_dep, get_storage_dep
from app.config import Settings
from app.models.database import Swing, SwingStatus
from app.models.schemas import SwingDetail, SwingSummary, UploadResponse, swing_to_detail
from app.services.dispatch import enqueue_processing
from app.services.storage import LocalStorage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/swings", tags=["swings"])


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_swing(
    file: UploadFile,
    handedness: Literal["right", "left"] | None = Form(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    storage: LocalStorage = Depends(get_storage_dep),
) -> UploadResponse:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.allowed_video_extensions:
        allowed = ", ".join(sorted(settings.allowed_video_extensions))
        raise HTTPException(415, f"unsupported video format {ext or '(none)'}; use one of: {allowed}")

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(413, f"video exceeds the {settings.max_upload_mb} MB upload limit")
    if not content:
        raise HTTPException(400, "uploaded file is empty")

    swing = Swing(
        original_filename=file.filename or f"swing{ext}",
        handedness=handedness or settings.default_handedness,
    )
    db.add(swing)
    db.commit()

    storage.save_original(swing.id, swing.original_filename, content)
    enqueue_processing(settings, swing.id)
    return UploadResponse(id=swing.id, status=swing.status)


@router.get("", response_model=list[SwingSummary])
def list_swings(db: Session = Depends(get_db)) -> list[SwingSummary]:
    swings = db.scalars(select(Swing).order_by(Swing.created_at.desc())).all()
    return [SwingSummary.model_validate(s) for s in swings]


@router.get("/{swing_id}", response_model=SwingDetail)
def get_swing(
    swing_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> SwingDetail:
    swing = db.get(Swing, swing_id)
    if swing is None:
        raise HTTPException(404, "swing not found")
    return swing_to_detail(swing, settings.api_v1_prefix)


@router.delete("/{swing_id}", status_code=204)
def delete_swing(
    swing_id: str,
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage_dep),
) -> None:
    swing = db.get(Swing, swing_id)
    if swing is None:
        raise HTTPException(404, "swing not found")
    if swing.status == SwingStatus.PROCESSING:
        raise HTTPException(409, "swing is still processing; try again when it finishes")
    db.delete(swing)
    db.commit()
    storage.delete_swing(swing_id)


@router.get("/{swing_id}/video/{artifact}")
def get_swing_artifact(
    swing_id: str,
    artifact: Literal["original", "source", "annotated", "thumbnail"],
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage_dep),
) -> FileResponse:
    if db.get(Swing, swing_id) is None:
        raise HTTPException(404, "swing not found")

    if artifact == "original":
        path = storage.original_path(swing_id)
    else:
        path = storage.artifact_path(swing_id, artifact)
    if path is None or not path.exists():
        raise HTTPException(404, f"{artifact} not available for this swing")

    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    # FileResponse handles HTTP Range requests, which <video> needs to seek.
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/{swing_id}/keypoints")
def get_swing_keypoints(
    swing_id: str,
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage_dep),
) -> dict:
    """Raw per-frame COCO-17 keypoints (for client-side overlays/debugging)."""
    if db.get(Swing, swing_id) is None:
        raise HTTPException(404, "swing not found")
    if not storage.artifact_exists(swing_id, "keypoints"):
        raise HTTPException(404, "keypoints not available for this swing")
    return storage.load_json(swing_id, "keypoints")
