"""Provenance guards on comparisons: the pipeline note and reference model tag.

Both are about the same failure — a metric gap blamed on the golfer when it is
really the pose settings — so both refuse to read those settings from anywhere
but the values recorded when each swing was actually processed.
"""
import argparse
import json
from types import SimpleNamespace

from app.api.routes.references import _pipeline_note
from app.config import Settings
from app.models.database import Swing


def _swing(pose_model: str | None = "yolo26m-pose.pt", pose_imgsz: int | None = 640) -> Swing:
    return Swing(pose_model=pose_model, pose_imgsz=pose_imgsz)


class TestPipelineNote:
    def test_reference_without_recorded_settings_admits_it(self):
        note = _pipeline_note({"pose_model": "yolo26m-pose.pt"}, _swing())
        assert note is not None
        assert "built before" in note

    def test_matching_settings_produce_no_note(self):
        profile = {"pose_imgsz": 640, "pose_model": "yolo26m-pose.pt"}
        assert _pipeline_note(profile, _swing(pose_imgsz=640)) is None

    def test_resolution_mismatch_uses_the_swings_recorded_value(self):
        # The swing was processed at 512; the reference was built at 640. The
        # note must read 512 off the swing, NOT the live pose_imgsz setting —
        # which is exactly the value that could have drifted since processing.
        profile = {"pose_imgsz": 640, "pose_model": "yolo26m-pose.pt"}
        note = _pipeline_note(profile, _swing(pose_imgsz=512))
        assert note is not None
        assert "inference resolution (640 vs 512)" in note

    def test_a_swing_matching_the_reference_is_never_flagged_on_resolution(self):
        # Regression for the old bug: the note compared the reference against the
        # global setting, so lowering pose_imgsz after processing falsely
        # discredited a swing that was genuinely measured at the reference's
        # resolution. The swing carries its own 640, so it stays clean.
        profile = {"pose_imgsz": 640, "pose_model": "yolo26m-pose.pt"}
        assert _pipeline_note(profile, _swing(pose_imgsz=640)) is None

    def test_model_mismatch_is_reported(self):
        profile = {"pose_imgsz": 640, "pose_model": "yolo26m-pose.pt"}
        note = _pipeline_note(profile, _swing(pose_imgsz=640, pose_model="yolo11m-pose.pt"))
        assert note is not None
        assert "pose model (yolo26m-pose.pt vs yolo11m-pose.pt)" in note

    def test_both_mismatches_are_joined(self):
        profile = {"pose_imgsz": 640, "pose_model": "yolo26m-pose.pt"}
        note = _pipeline_note(profile, _swing(pose_imgsz=512, pose_model="yolo11m-pose.pt"))
        assert note is not None
        assert "inference resolution (640 vs 512)" in note
        assert "pose model (yolo26m-pose.pt vs yolo11m-pose.pt)" in note
        assert " and " in note

    def test_swing_without_recorded_resolution_is_not_falsely_flagged(self):
        # An older swing predating the pose_imgsz column: we cannot know its
        # resolution, so we say nothing about it rather than inventing a mismatch.
        profile = {"pose_imgsz": 640, "pose_model": "yolo26m-pose.pt"}
        assert _pipeline_note(profile, _swing(pose_imgsz=None)) is None


class TestReferenceRecordsLoadedModel:
    """build_reference must tag a reference with the model that actually loaded.

    When the primary weights are unavailable the estimator falls back; recording
    the configured name instead would flag a false model mismatch against every
    swing (which records the same fallback).
    """

    def test_profile_records_the_estimators_model_not_the_configured_one(
        self, tmp_path, monkeypatch
    ):
        from scripts import build_reference as br

        settings = Settings(
            storage_dir=tmp_path / "storage",
            database_url=f"sqlite:///{tmp_path}/t.db",
            anthropic_api_key="",
            pose_model="yolo26m-pose.pt",  # configured primary...
        )
        # ...but the loaded estimator reports the fallback it fell back to.
        fallback = "yolo11m-pose.pt"

        monkeypatch.setattr(br, "get_settings", lambda: settings)
        monkeypatch.setattr(
            br, "create_pose_estimator", lambda _s: SimpleNamespace(model_name=fallback)
        )
        monkeypatch.setattr(br.vp, "normalize_video", lambda *a, **k: None)
        monkeypatch.setattr(
            br.vp, "probe",
            lambda _p: SimpleNamespace(n_frames=10, fps=30.0, width=640, height=480, duration=0.3),
        )
        monkeypatch.setattr(br.vp, "save_thumbnail", lambda *a, **k: None)
        monkeypatch.setattr(br.vp, "extract_keypoints", lambda *a, **k: object())
        monkeypatch.setattr(
            br, "smooth_series",
            lambda *a, **k: SimpleNamespace(to_json_payload=lambda: {"meta": {}}),
        )
        monkeypatch.setattr(
            br, "detect_phases", lambda *a, **k: SimpleNamespace(segments=[], events={})
        )
        monkeypatch.setattr(
            br, "compute_metrics",
            lambda *a, **k: {"camera": {"view": "down_the_line", "frontality": 0.1}, "summary": []},
        )

        args = argparse.Namespace(
            input="dummy.mp4", id="ref-test", display_name="Test",
            handedness="right", source="self-filmed", license="owned",
        )
        assert br.build(args) == 0

        profile = json.loads(
            (settings.storage_dir / "references" / "ref-test" / "profile.json").read_text()
        )
        assert profile["pose_model"] == fallback
