import json

import numpy as np
import pytest

from app.services.metric_calculator import (
    FRONTALITY_FACE_ON,
    MIN_LIMB_RATIO,
    MIN_LINE_RATIO,
    ROTATION_METRIC_KEYS,
    _apply_camera_reliability,
    _compute_delta,
    _joint_angle_masked,
    _lead_arm_entry,
    classify_view,
    compute_metrics,
    joint_angle_deg,
    joint_angle_masked,
    line_angle_deg,
    line_angle_masked,
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


class TestCameraView:
    def test_classify_boundaries(self):
        assert classify_view(0.60) == "face_on"
        assert classify_view(FRONTALITY_FACE_ON) == "face_on"
        assert classify_view(0.35) == "oblique"
        assert classify_view(0.10) == "down_the_line"
        assert classify_view(None) == "unknown"

    def test_synthetic_swing_is_recognised_as_face_on(self, analysis):
        """The synthetic swing is constructed face-on; if this ever flips, the
        thresholds have drifted away from the only ground truth we have."""
        metrics, _ = analysis
        assert metrics["camera"]["view"] == "face_on"
        assert metrics["camera"]["rotation_measurable"] is True

    def test_face_on_keeps_rotation_metrics_judged(self, analysis):
        metrics, _ = analysis
        rot = [e for e in metrics["summary"] if e["key"] in ROTATION_METRIC_KEYS]
        assert rot
        assert all(e["reliable"] for e in rot)

    def test_down_the_line_strips_the_verdict_but_keeps_the_number(self):
        summary = [
            {"key": "shoulder_turn_at_top", "value": 12.1, "assessment": "watch",
             "delta": -47.9, "delta_normalized": 0.8, "reliable": True,
             "unreliable_reason": None},
            {"key": "early_extension", "value": 5.5, "assessment": "good",
             "delta": 0.0, "delta_normalized": 0.0, "reliable": True,
             "unreliable_reason": None},
        ]
        out = _apply_camera_reliability(summary, "down_the_line")
        rot, posture = out[0], out[1]

        assert rot["value"] == 12.1          # the projection really does show this
        assert rot["reliable"] is False
        assert rot["assessment"] is None     # but it is not a verdict
        assert rot["delta"] is None
        assert "camera axis" in rot["unreliable_reason"]

        assert posture["reliable"] is True   # posture survives every view
        assert posture["assessment"] == "good"

    def test_oblique_also_downgrades_rotation(self):
        summary = [{"key": "x_factor_at_top", "value": 20.0, "assessment": "watch",
                    "delta": -5.0, "delta_normalized": 0.1, "reliable": True,
                    "unreliable_reason": None}]
        out = _apply_camera_reliability(summary, "oblique")
        assert out[0]["reliable"] is False
        assert "oblique" in out[0]["unreliable_reason"]

    def test_frontality_is_measured_at_address_not_across_the_swing(self, analysis):
        """Across the whole swing a down-the-line golfer's shoulders open up and
        the ratio converges on the face-on value. Address is where they differ."""
        metrics, _ = analysis
        assert metrics["camera"]["frontality"] is not None


class TestJointAngleMasking:
    """A limb pointing at the lens projects short, and the interior angle at its
    joint is foreshortened: a straight arm seen end-on measures bent."""

    def test_a_well_projected_limb_keeps_its_angle(self):
        a = np.array([[0.0, 100.0]])
        b = np.array([[0.0, 0.0]])
        c = np.array([[100.0, 0.0]])
        scale = np.array([100.0])
        assert joint_angle_masked(a, b, c, scale)[0] == pytest.approx(90.0)

    def test_a_foreshortened_limb_is_masked(self):
        a = np.array([[0.0, 10.0]])  # 10 / 100 = 0.1, far under the threshold
        b = np.array([[0.0, 0.0]])
        c = np.array([[100.0, 0.0]])
        scale = np.array([100.0])
        assert np.isnan(joint_angle_masked(a, b, c, scale)[0])

    def test_the_shorter_limb_decides(self):
        """One long segment cannot rescue an angle read off a collapsed one."""
        long_ok = MIN_LIMB_RATIO * 100 + 20
        too_short = MIN_LIMB_RATIO * 100 - 5
        b = np.array([[0.0, 0.0], [0.0, 0.0]])
        a = np.array([[0.0, long_ok], [0.0, too_short]])
        c = np.array([[long_ok, 0.0], [long_ok, 0.0]])
        out = joint_angle_masked(a, b, c, np.array([100.0, 100.0]))
        assert not np.isnan(out[0])
        assert np.isnan(out[1])

    def test_a_straight_arm_seen_end_on_would_have_read_bent(self):
        """Why the guard exists, shown on the unmasked helper."""
        shoulder = np.array([[0.0, 0.0]])
        elbow = np.array([[10.0, 2.0]])   # arm nearly along the camera axis
        wrist = np.array([[18.0, 12.0]])
        bent = joint_angle_deg(shoulder, elbow, wrist)[0]
        assert bent < 140  # the arm is straight in 3D; the projection disagrees

    def test_lead_arm_survives_on_the_face_on_synthetic_swing(self, analysis):
        metrics, _ = analysis
        lead_arm = next(e for e in metrics["summary"] if e["key"] == "lead_arm_at_top")
        assert lead_arm["value"] is not None
        assert lead_arm["reliable"] is True


class TestForeshorteningFlag:
    """The mask must say *why* it dropped a frame: a limb pointing at the lens is
    a different thing from a limb that was never detected."""

    def test_a_well_projected_limb_is_not_flagged(self):
        a = np.array([[0.0, 100.0]])
        b = np.array([[0.0, 0.0]])
        c = np.array([[100.0, 0.0]])
        masked, foreshortened = _joint_angle_masked(a, b, c, np.array([100.0]))
        assert masked[0] == pytest.approx(90.0)
        assert not foreshortened[0]

    def test_a_foreshortened_limb_is_flagged(self):
        a = np.array([[0.0, 10.0]])  # 10 / 100 = 0.1, well under the threshold
        b = np.array([[0.0, 0.0]])
        c = np.array([[100.0, 0.0]])
        masked, foreshortened = _joint_angle_masked(a, b, c, np.array([100.0]))
        assert np.isnan(masked[0])
        assert foreshortened[0]

    def test_missing_keypoints_are_not_called_foreshortened(self):
        # a == b == c is degenerate (no angle at all). That is "not detected",
        # not "pointing at the camera", so it must not be flagged.
        p = np.array([[1.0, 1.0]])
        masked, foreshortened = _joint_angle_masked(p, p, p, np.array([100.0]))
        assert np.isnan(masked[0])
        assert not foreshortened[0]


class TestLeadArmEntry:
    """A foreshortened lead arm is masked, but the blank is explained rather than
    left bare — the failure the mask introduced on face-on swings."""

    @staticmethod
    def _signals(value: float, foreshortened: bool) -> dict:
        return {"lead_arm": np.array([value]),
                "lead_arm_foreshortened": np.array([foreshortened])}

    def test_a_measurable_value_is_reliable(self):
        entry = _lead_arm_entry(self._signals(165.0, False), "lead_arm_at_top",
                                "Lead arm", 0, (150.0, 180.0), "desc")
        assert entry["value"] == 165.0
        assert entry["reliable"] is True
        assert entry["unreliable_reason"] is None

    def test_a_foreshortened_blank_is_explained(self):
        entry = _lead_arm_entry(self._signals(np.nan, True), "lead_arm_at_top",
                                "Lead arm", 0, (150.0, 180.0), "desc")
        assert entry["value"] is None
        assert entry["reliable"] is False
        assert "foreshortened" in entry["unreliable_reason"]

    def test_a_missing_value_is_not_blamed_on_foreshortening(self):
        # NaN with no foreshortening flag: the keypoints simply were not there.
        # We do not claim the arm pointed at the lens, so the entry stays
        # reliable-but-empty rather than inventing a reason.
        entry = _lead_arm_entry(self._signals(np.nan, False), "lead_arm_at_top",
                                "Lead arm", 0, (150.0, 180.0), "desc")
        assert entry["value"] is None
        assert entry["reliable"] is True
        assert entry["unreliable_reason"] is None


class TestDelta:
    def test_in_range_is_zero(self):
        assert _compute_delta(5.0, (0.0, 10.0)) == (0.0, 0.0)

    def test_below_range_is_negative(self):
        delta, _ = _compute_delta(-3.0, (0.0, 10.0))
        assert delta == -3.0

    def test_above_range_is_positive(self):
        delta, _ = _compute_delta(14.0, (0.0, 10.0))
        assert delta == 4.0

    def test_none_value_or_range_yields_none(self):
        assert _compute_delta(None, (0.0, 10.0)) == (None, None)
        assert _compute_delta(5.0, None) == (None, None)

    def test_normalized_ranks_a_narrow_band_as_worse(self):
        """The same 7-unit miss matters more on a tight range."""
        _, wide = _compute_delta(127.0, (60.0, 120.0))    # width 60
        _, narrow = _compute_delta(15.0, (-6.0, 8.0))     # width 14
        assert narrow > wide

    def test_normalized_is_unsigned(self):
        _, below = _compute_delta(-4.0, (0.0, 10.0))
        _, above = _compute_delta(14.0, (0.0, 10.0))
        assert below > 0 and above > 0

    def test_sign_is_geometric_not_badness(self):
        """early_extension is lower_is_better, but a value above its band still
        produces a positive delta. Badness lives in `lower_is_better`."""
        delta, _ = _compute_delta(14.0, (-6.0, 8.0))
        assert delta == 6.0

    def test_summary_entries_carry_delta(self, analysis):
        metrics, _ = analysis
        for entry in metrics["summary"]:
            assert "delta" in entry and "delta_normalized" in entry
            if entry["value"] is None or entry["ideal_range"] is None:
                assert entry["delta"] is None

    def test_unbounded_metric_has_no_delta(self, analysis):
        """x_factor_stretch has no published ideal band; that is honest, not a gap."""
        metrics, _ = analysis
        stretch = next(e for e in metrics["summary"] if e["key"] == "x_factor_stretch")
        assert stretch["ideal_range"] is None
        assert stretch["delta"] is None


class TestLineAngleMasking:
    """A line seen end-on has no trustworthy angle: at a few pixels of
    separation, one pixel of pose noise swings it tens of degrees."""

    def test_well_separated_line_keeps_its_angle(self):
        a = np.array([[0.0, 0.0]])
        b = np.array([[100.0, 0.0]])
        scale = np.array([100.0])
        assert line_angle_masked(a, b, scale)[0] == pytest.approx(0.0)

    def test_foreshortened_line_is_masked(self):
        a = np.array([[0.0, 0.0]])
        b = np.array([[5.0, 0.0]])  # 5 / 100 = 0.05, well under the threshold
        scale = np.array([100.0])
        assert np.isnan(line_angle_masked(a, b, scale)[0])

    def test_threshold_boundary(self):
        scale = np.array([100.0, 100.0])
        a = np.zeros((2, 2))
        just_under = MIN_LINE_RATIO * 100 - 1
        just_over = MIN_LINE_RATIO * 100 + 1
        b = np.array([[just_under, 0.0], [just_over, 0.0]])
        out = line_angle_masked(a, b, scale)
        assert np.isnan(out[0])
        assert not np.isnan(out[1])

    def test_noise_on_a_short_line_would_have_swung_the_angle(self):
        """Demonstrates why the guard exists, using the unmasked helper."""
        a = np.array([[0.0, 0.0], [0.0, 0.0]])
        b = np.array([[4.0, 0.0], [4.0, 2.0]])  # 2px of vertical noise
        swing = abs(line_angle_deg(a, b)[1] - line_angle_deg(a, b)[0])
        assert swing > 25  # ~26.6 degrees from two pixels


class TestKinematicSequenceHonesty:
    def test_declines_when_rotation_is_unmeasurable(self, analysis):
        """Zero-filling a masked frame manufactures a velocity spike, and the
        spike decides the ordering. Declining is the honest answer."""
        metrics, _ = analysis
        ks = metrics["kinematic_sequence"]
        if ks["available"]:
            # Synthetic swing is face-on and well conditioned; the ordering must
            # then rest on real motion, never on a NaN-derived spike.
            assert set(ks["order"]) == {"hips", "torso", "arms"}
        else:
            assert "not measurable" in ks["reason"]


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


class TestCoachingRequest:
    """Guards on the request we send. Thinking tokens come out of max_tokens, so
    leaving thinking on truncates the JSON and the report is silently dropped."""

    def _capture(self, monkeypatch):
        from app.services import coaching

        sent: dict = {}

        class FakeMessages:
            def parse(self, **kwargs):
                sent.update(kwargs)
                raise RuntimeError("stop here — we only inspect the request")

        class FakeClient:
            messages = FakeMessages()

        monkeypatch.setattr(coaching, "_client_singleton", None)
        monkeypatch.setattr(coaching, "_cached_client", lambda _key: FakeClient())
        return sent

    def test_thinking_is_disabled(self, analysis, settings, monkeypatch):
        from app.services.coaching import generate_coaching

        sent = self._capture(monkeypatch)
        metrics, phases = analysis
        settings = settings.model_copy(update={"anthropic_api_key": "sk-test"})

        # The broad except swallows our RuntimeError; we assert on what was sent.
        assert generate_coaching(metrics, phases.segments, "right", settings) is None
        assert sent["thinking"] == {"type": "disabled"}

    def test_uses_structured_output_helper(self, analysis, settings, monkeypatch):
        from app.services.coaching import CoachingReport, generate_coaching

        sent = self._capture(monkeypatch)
        metrics, phases = analysis
        settings = settings.model_copy(update={"anthropic_api_key": "sk-test"})

        generate_coaching(metrics, phases.segments, "right", settings)
        assert sent["output_format"] is CoachingReport
        assert sent["max_tokens"] == settings.coaching_max_tokens

    def test_client_is_reused_across_calls(self, monkeypatch):
        from app.services import coaching

        monkeypatch.setattr(coaching, "_client_singleton", None)
        created: list[str] = []

        class FakeAnthropic:
            def __init__(self, api_key):
                created.append(api_key)

        monkeypatch.setitem(
            __import__("sys").modules, "anthropic",
            type("m", (), {"Anthropic": FakeAnthropic}),
        )
        first = coaching._cached_client("sk-test")
        second = coaching._cached_client("sk-test")
        assert first is second
        assert created == ["sk-test"]
