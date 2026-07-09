"""Read-only access to pre-built reference swings.

A reference is a swing we processed once, offline, and froze:

    {storage_dir}/references/
        index.json                  manifest of every reference
        {ref_id}/
            profile.json            display_name, handedness, camera_angle, source, license
            keypoints.json          smoothed COCO-17 series (the one metrics were computed from)
            phases.json             {segments, events}
            metrics.json            compute_metrics() output
            source.mp4              optional playable clip

References deliberately do not use the `Swing` table or the upload pipeline.
They have no status, no progress, no owner, and they never change. Adding a
table for five frozen artifacts would mean introducing migrations to a project
whose schema comes from `create_all`, for no gain.

`display_name`, `source`, and `license` are data, not code, so renaming a
reference or swapping the asset underneath it is an edit to a JSON file.
"""
import json
import logging
from pathlib import Path

from app.config import Settings

logger = logging.getLogger(__name__)

REFERENCE_FILES = {
    "profile": "profile.json",
    "keypoints": "keypoints.json",
    "phases": "phases.json",
    "metrics": "metrics.json",
    "source": "source.mp4",
    "thumbnail": "thumbnail.jpg",
}


class ReferenceNotFound(LookupError):
    pass


class ReferenceLibrary:
    def __init__(self, settings: Settings):
        self.root = Path(settings.storage_dir) / "references"

    # -- paths -------------------------------------------------------------
    def reference_dir(self, ref_id: str) -> Path:
        if "/" in ref_id or ".." in ref_id:  # the id lands in a filesystem path
            raise ReferenceNotFound(ref_id)
        return self.root / ref_id

    def file_path(self, ref_id: str, name: str) -> Path:
        if name not in REFERENCE_FILES:
            raise KeyError(f"unknown reference file {name!r}")
        return self.reference_dir(ref_id) / REFERENCE_FILES[name]

    # -- reads -------------------------------------------------------------
    def list(self) -> list[dict]:
        index = self.root / "index.json"
        if not index.exists():
            return []
        try:
            return json.loads(index.read_text()).get("references", [])
        except (OSError, json.JSONDecodeError):
            logger.exception("reference index unreadable at %s", index)
            return []

    def exists(self, ref_id: str) -> bool:
        return self.file_path(ref_id, "profile").exists()

    def load(self, ref_id: str, name: str) -> dict:
        path = self.file_path(ref_id, name)
        if not path.exists():
            raise ReferenceNotFound(f"{ref_id}/{name}")
        return json.loads(path.read_text())

    def profile(self, ref_id: str) -> dict:
        return self.load(ref_id, "profile")

    def metrics(self, ref_id: str) -> dict:
        return self.load(ref_id, "metrics")

    def phases(self, ref_id: str) -> dict:
        return self.load(ref_id, "phases")

    def has_video(self, ref_id: str) -> bool:
        return self.file_path(ref_id, "source").exists()


def get_reference_library(settings: Settings) -> ReferenceLibrary:
    return ReferenceLibrary(settings)
