import json

import numpy as np
import pytest

from app.services.metric_calculator import (
    compute_metrics,
    joint_angle_deg,
    line_angle_deg,
    vertical_tilt_deg,
)
from app.services.phase_detector import detect_phases

from tests.synthetic import make_swing_series


class TestGeometryHelpers:
    def test_joint_angle_right_angle(self):
        a = np.array([[1.0, 0.0]])
        b = np.array([[0.0, 0.0]])
        c = np.array([[0.0, 1.0]])
        assert joint_angle_deg(a, b, c)[0] == pytest.approx(90.0)

    def test_joint_angle_straight_limb(self):
        a = np.array([[0.0, 0.0]])
        b = np.array([[1.0, 1.0]])
        c = np.array([[2.0, 2.0]])
        assert joint_angle_deg(a, b, c)[0] == pytest.approx(180.0)

    def test_joint_angle_degenerate_is_nan(self):
        p = np.array([[1.0, 1.0]])
        assert np.isnan(joint_angle_deg(p, p, p)[0])

    def test_line_angle_horizontal_is_zero(self):
        a = np.array([[0.0, 5.0]])
        b = np.array([[10.0, 5.0]])
        assert line_angle_deg(a, b)[0] == pytest.approx(0.0)

    def test_line_angle_up_is_positive(self):
        # b above a in image coords (smaller y) -> positive angle
        a = np.array([[0.0, 10.0]])
        b = np.array([[10.0, 0.0]])
        assert line_angle_deg(a, b)[0] == pytest.approx(45.0)

    def test_vertical_tilt(self):
        bottom = np.array([[0.0, 10.0]])
        straight_up = np.array([[0.0, 0.0]])
        tilted = np.array([[10.0, 0.0]])
        assert vertical_tilt_deg(bottom, straight_up)[0] == pytest.approx(0.0)
        assert vertical_tilt_deg(bottom, tilted)[0] == pytest.approx(45.0)


@pytest.fixture(scope="module")
def analysis():
    series, _ = make_swing_series()
    phases = detect_phases(series)
    return compute_metrics(series, phases, handedness="right"), phases


class TestSwingMetrics:
    def test_payload_is_json_safe(self, analysis):
        metrics, _ = analysis
        encoded = json.dumps(metrics, allow_nan=False)  # raises on NaN/inf
        assert "NaN" not in encoded

    def test_tempo_in_plausible_range(self, analysis):
        metrics, _ = analysis
        tempo = next(e for e in metrics["summary"] if e["key"] == "tempo_ratio")
        assert tempo["value"] is not None
        assert 1.5 < tempo["value"] < 5.0

    def test_shoulders_turn_more_than_hips(self, analysis):
        metrics, _ = analysis
        by_key = {e["key"]: e["value"] for e in metrics["summary"]}
        assert by_key["shoulder_turn_at_top"] > by_key["hip_turn_at_top"] > 0

    def test_x_factor_positive_at_top(self, analysis):
        metrics, _ = analysis
        by_key = {e["key"]: e["value"] for e in metrics["summary"]}
        assert by_key["x_factor_at_top"] > 5.0

    def test_stable_head_scores_well(self, analysis):
        metrics, _ = analysis
        head = next(e for e in metrics["summary"] if e["key"] == "head_stability")
        assert head["value"] is not None
        assert head["value"] < 0.3  # synthetic head never moves
        assert head["assessment"] == "good"

    def test_series_lengths_match_video(self, analysis):
        metrics, phases = analysis
        n = len(phases.frame_labels)
        for name, values in metrics["series"].items():
            assert len(values) == n, name

    def test_kinematic_sequence_available(self, analysis):
        metrics, _ = analysis
        seq = metrics["kinematic_sequence"]
        assert seq["available"] is True
        assert sorted(seq["order"]) == ["arms", "hips", "torso"]

    def test_assessments_computed_from_ranges(self, analysis):
        metrics, _ = analysis
        for entry in metrics["summary"]:
            if entry["value"] is not None and entry["ideal_range"] is not None:
                lo, hi = entry["ideal_range"]
                expected = "good" if lo <= entry["value"] <= hi else "watch"
                assert entry["assessment"] == expected, entry["key"]

    def test_includes_2d_limitation_notes(self, analysis):
        metrics, _ = analysis
        assert any("2D" in note for note in metrics["notes"])


class TestCoachingPrompt:
    def test_prompt_contains_metrics_and_request(self, analysis):
        from app.services.coaching import build_coaching_prompt

        metrics, phases = analysis
        prompt = build_coaching_prompt(metrics, phases.segments, "right")
        assert "Tempo" in prompt
        assert "drill" in prompt.lower()
        assert "right" in prompt

    def test_generate_coaching_skips_without_api_key(self, analysis, settings):
        from app.services.coaching import generate_coaching

        metrics, phases = analysis
        assert generate_coaching(metrics, phases.segments, "right", settings) is None
