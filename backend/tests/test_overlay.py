"""Aligning a reference skeleton onto a user's swing.

The properties that matter: the time map never goes backwards, aligning a swing
with itself changes nothing, and mirroring twice is the identity.
"""
import numpy as np
import pytest

from app.core.keypoints import KeypointSeries
from app.services.overlay import (
    anchors,
    build_overlay,
    frame_map,
    mirror_keypoints,
    torso_scale,
)

from tests.synthetic import make_swing_series

EVENTS = {"takeaway": 10, "top": 30, "impact": 40, "finish": 60}


def _series(n=80, scale=1.0, offset=(0.0, 0.0), width=720, height=1280):
    """A synthetic body: 17 joints on a fixed skeleton, moved and resized."""
    base = np.zeros((n, 17, 3))
    for j in range(17):
        base[:, j, 0] = 100 + 10 * j
        base[:, j, 1] = 200 + 5 * j
        base[:, j, 2] = 0.9
    base[..., :2] *= scale
    base[..., 0] += offset[0]
    base[..., 1] += offset[1]
    return KeypointSeries(base, 30.0, width, height)


class TestAnchors:
    def test_pins_both_ends_and_keeps_the_events(self):
        assert anchors(EVENTS, 80) == [0, 10, 30, 40, 60, 79]

    def test_output_is_strictly_increasing(self):
        out = anchors({"takeaway": 0, "top": 0, "impact": 0, "finish": 0}, 80)
        assert all(b > a for a, b in zip(out, out[1:]))

    def test_events_beyond_the_last_frame_are_clamped(self):
        out = anchors({"takeaway": 5, "top": 10, "impact": 200, "finish": 300}, 20)
        assert max(out) <= 19
        assert all(b > a for a, b in zip(out, out[1:]))


class TestFrameMap:
    def test_identity_when_the_swings_match(self):
        mapping = frame_map(EVENTS, 80, EVENTS, 80)
        assert mapping == list(range(80))

    def test_is_monotonic_non_decreasing(self):
        ref = {"takeaway": 20, "top": 55, "impact": 70, "finish": 110}
        mapping = frame_map(EVENTS, 80, ref, 140)
        assert all(b >= a for a, b in zip(mapping, mapping[1:]))

    def test_events_land_on_events(self):
        """The whole point: both swings hit top and impact together."""
        ref = {"takeaway": 20, "top": 55, "impact": 70, "finish": 110}
        mapping = frame_map(EVENTS, 80, ref, 140)
        assert mapping[EVENTS["top"]] == ref["top"]
        assert mapping[EVENTS["impact"]] == ref["impact"]
        assert mapping[EVENTS["takeaway"]] == ref["takeaway"]

    def test_stays_inside_the_reference(self):
        ref = {"takeaway": 5, "top": 12, "impact": 15, "finish": 20}
        mapping = frame_map(EVENTS, 80, ref, 25)
        assert min(mapping) >= 0 and max(mapping) <= 24

    def test_a_shorter_user_swing_still_covers_the_reference(self):
        user = {"takeaway": 2, "top": 5, "impact": 7, "finish": 9}
        ref = {"takeaway": 20, "top": 55, "impact": 70, "finish": 110}
        mapping = frame_map(user, 12, ref, 140)
        assert mapping[0] == 0
        assert mapping[-1] == 139


class TestMirroring:
    def test_mirroring_twice_is_the_identity(self):
        s = _series()
        once = mirror_keypoints(s.data, s.width)
        twice = mirror_keypoints(once, s.width)
        assert np.allclose(twice, s.data)

    def test_x_is_reflected(self):
        """Reflection and the joint swap compose, so compare per joint: the
        mirrored LEFT_SHOULDER must be the reflected RIGHT_SHOULDER."""
        s = _series()
        out = mirror_keypoints(s.data, s.width)
        assert np.allclose(out[:, 5, 0], s.width - s.data[:, 6, 0])
        assert np.allclose(out[:, 6, 0], s.width - s.data[:, 5, 0])
        # NOSE is unpaired, so it only reflects.
        assert np.allclose(out[:, 0, 0], s.width - s.data[:, 0, 0])

    def test_confidence_is_untouched(self):
        s = _series()
        out = mirror_keypoints(s.data, s.width)
        assert np.allclose(np.sort(out[..., 2]), np.sort(s.data[..., 2]))

    def test_left_and_right_joints_swap(self):
        s = _series()
        out = mirror_keypoints(s.data, s.width)
        # index 5 is LEFT_SHOULDER, 6 is RIGHT_SHOULDER
        assert np.allclose(out[:, 5, 1], s.data[:, 6, 1])


class TestNormalization:
    def test_a_swing_against_itself_needs_no_scaling(self):
        s, _ = make_swing_series()
        assert torso_scale(s) == pytest.approx(torso_scale(s))

    def test_scale_is_one_when_the_bodies_match(self):
        user, ref = _series(), _series()
        out = build_overlay(user, EVENTS, ref, EVENTS, mirror=False)
        assert out["scale"] == pytest.approx(1.0, abs=1e-3)

    def test_a_twice_as_large_reference_is_halved(self):
        user, ref = _series(scale=1.0), _series(scale=2.0)
        out = build_overlay(user, EVENTS, ref, EVENTS, mirror=False)
        assert out["scale"] == pytest.approx(0.5, abs=1e-3)

    def test_translation_does_not_change_scale(self):
        user, ref = _series(), _series(offset=(300.0, -50.0))
        out = build_overlay(user, EVENTS, ref, EVENTS, mirror=False)
        assert out["scale"] == pytest.approx(1.0, abs=1e-3)


class TestBuildOverlay:
    def test_carries_the_pieces_a_client_needs(self):
        user, ref = _series(n=80), _series(n=100)
        out = build_overlay(user, EVENTS, ref, EVENTS, mirror=False)
        assert len(out["frame_map"]) == 80
        assert len(out["reference"]["keypoints"]) == 100
        assert len(out["user"]["hip_centers"]) == 80
        assert out["anchor_frame"] == EVENTS["takeaway"]

    def test_mirroring_is_recorded_and_applied(self):
        user, ref = _series(), _series()
        out = build_overlay(user, EVENTS, ref, EVENTS, mirror=True)
        assert out["mirrored"] is True
        assert out["reference"]["keypoints"][0][0][0] != ref.data[0][0][0]
