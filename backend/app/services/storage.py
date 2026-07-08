"""File storage abstraction.

All artifacts for a swing live under one directory keyed by swing id:

    {storage_dir}/swings/{swing_id}/
        original.<ext>    exact bytes the user uploaded
        source.mp4        normalized H.264 copy used for processing/playback
        annotated.mp4     skeleton + phase overlay render
        thumbnail.jpg     poster frame for the history page
        keypoints.json    raw per-frame COCO-17 keypoints

The interface is deliberately path-shaped-but-opaque: callers ask for named
artifacts and get local Paths back. Swapping in S3/MinIO later means
implementing these same methods against object keys and presigned URLs
without touching the pipeline.
"""
import json
import shutil
from pathlib import Path

from app.config import Settings

# Canonical artifact names; single source of truth for pipeline and API.
ARTIFACTS = {
    "source": "source.mp4",
    "annotated": "annotated.mp4",
    "thumbnail": "thumbnail.jpg",
    "keypoints": "keypoints.json",
}


class LocalStorage:
    def __init__(self, settings: Settings):
        self.root = Path(settings.storage_dir)

    def swing_dir(self, swing_id: str) -> Path:
        d = self.root / "swings" / swing_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_original(self, swing_id: str, filename: str, content: bytes) -> Path:
        ext = Path(filename).suffix.lower()
        path = self.swing_dir(swing_id) / f"original{ext}"
        path.write_bytes(content)
        return path

    def original_path(self, swing_id: str) -> Path | None:
        matches = sorted(self.swing_dir(swing_id).glob("original.*"))
        return matches[0] if matches else None

    def artifact_path(self, swing_id: str, artifact: str) -> Path:
        if artifact not in ARTIFACTS:
            raise KeyError(f"unknown artifact {artifact!r}")
        return self.swing_dir(swing_id) / ARTIFACTS[artifact]

    def artifact_exists(self, swing_id: str, artifact: str) -> bool:
        return self.artifact_path(swing_id, artifact).exists()

    def save_json(self, swing_id: str, artifact: str, payload: dict) -> Path:
        path = self.artifact_path(swing_id, artifact)
        path.write_text(json.dumps(payload))
        return path

    def load_json(self, swing_id: str, artifact: str) -> dict:
        return json.loads(self.artifact_path(swing_id, artifact).read_text())

    def delete_swing(self, swing_id: str) -> None:
        shutil.rmtree(self.swing_dir(swing_id), ignore_errors=True)


def get_storage(settings: Settings) -> LocalStorage:
    return LocalStorage(settings)
